package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"strings"
	"time"

	promapi "github.com/prometheus/client_golang/api"
	promv1 "github.com/prometheus/client_golang/api/prometheus/v1"
	"github.com/prometheus/common/model"
	ort "github.com/yalue/onnxruntime_go"
	v1 "k8s.io/api/core/v1"
	k8sruntime "k8s.io/apimachinery/pkg/runtime"
	"k8s.io/component-base/logs"
	"k8s.io/kubernetes/cmd/kube-scheduler/app"
	"k8s.io/kubernetes/pkg/scheduler/framework"
)

const (
	Name      = "GreenScheduler"
	ModelPath = "energy_model.onnx"
	LibPath   = "/usr/local/lib/libonnxruntime.so"
	PromURL   = "http://127.0.0.1:9090"
)

type GreenScore struct {
	handle  framework.Handle
	session *ort.DynamicAdvancedSession
	promAPI promv1.API
}

var _ framework.ScorePlugin = &GreenScore{}

func (gs *GreenScore) Name() string { return Name }

// Fetches the Node's baseline power from Kepler
func (gs *GreenScore) getNodePower(ctx context.Context, nodeName string) float64 {
	query := fmt.Sprintf(`sum by (exported_instance) (rate(kepler_node_platform_joules_total{exported_instance="%s"}[1m]))`, nodeName)
	result, _, err := gs.promAPI.Query(ctx, query, time.Now())
	if err != nil { return 0 }
	
	vector, ok := result.(model.Vector)
	if !ok || len(vector) == 0 { return 0 }
	return float64(vector[0].Value)
}

// NEW: Fetches live average RX/TX bytes for a specific cohort of pods
func (gs *GreenScore) getPodTraffic(ctx context.Context, podKeyword string) (float32, float32) {
	// Fallback to 1000 bytes/sec if no other pods of this type are running yet
	rxFallback, txFallback := float32(1000.0), float32(1000.0)

	queryRX := fmt.Sprintf(`avg(rate(container_network_receive_bytes_total{pod=~".*%s.*"}[1m]))`, podKeyword)
	queryTX := fmt.Sprintf(`avg(rate(container_network_transmit_bytes_total{pod=~".*%s.*"}[1m]))`, podKeyword)

	rx := gs.queryPrometheusValue(ctx, queryRX, rxFallback)
	tx := gs.queryPrometheusValue(ctx, queryTX, txFallback)

	return rx, tx
}

// Helper to execute Prometheus queries for float32 returns
func (gs *GreenScore) queryPrometheusValue(ctx context.Context, query string, fallback float32) float32 {
	result, _, err := gs.promAPI.Query(ctx, query, time.Now())
	if err != nil { return fallback }
	
	vector, ok := result.(model.Vector)
	if !ok || len(vector) == 0 { return fallback }
	return float32(vector[0].Value)
}

func (gs *GreenScore) Score(ctx context.Context, state *framework.CycleState, p *v1.Pod, nodeName string) (int64, *framework.Status) {
	nodePowerWatts := gs.getNodePower(ctx, nodeName)

	cpu := float32(p.Spec.Containers[0].Resources.Requests.Cpu().AsApproximateFloat64())
	mem := float32(p.Spec.Containers[0].Resources.Requests.Memory().Value())
	
	// Dynamically determine pod cohort and fetch real-time network load
	var podKeyword string
	podType := float32(2.0)
	
	if anyIn(p.Name, "srsran", "gnb", "ue") { 
		podType = 0.0
		podKeyword = "srsran"
	} else if anyIn(p.Name, "open5gs", "amf", "upf") { 
		podType = 1.0
		podKeyword = "open5gs"
	} else {
		podKeyword = "test" // Covers our test-green-pod
	}

	netRx, netTx := gs.getPodTraffic(ctx, podKeyword)

	// Features now include live network load instead of static 50000.0
	inputData := []float32{cpu, mem, netRx, netTx, podType}

	inputShape := ort.NewShape(1, 5)
	inputTensor, _ := ort.NewTensor(inputShape, inputData)
	defer inputTensor.Destroy()

	outputData := make([]float32, 1)
	outputShape := ort.NewShape(1, 1)
	outputTensor, _ := ort.NewTensor(outputShape, outputData)
	defer outputTensor.Destroy()

	_ = gs.session.Run([]ort.Value{inputTensor}, []ort.Value{outputTensor})
	podPredictedCost := float64(outputData[0])

	totalEnergyCost := nodePowerWatts + (podPredictedCost / 10)
	score := int64(200 - totalEnergyCost)
	
	if score < 0 { score = 0 }
	if score > 100 { score = 100 }

	log.Printf("Pod: %s | Node: %s | NodePower: %.2fW | NetRX: %.2f | NetTX: %.2f | PodCost: %.2f | Score: %d", 
		p.Name, nodeName, nodePowerWatts, netRx, netTx, podPredictedCost, score)
		
	return score, framework.NewStatus(framework.Success, "")
}

func anyIn(s string, keywords ...string) bool {
	for _, k := range keywords {
		if strings.Contains(s, k) { return true }
	}
	return false
}

func (gs *GreenScore) ScoreExtensions() framework.ScoreExtensions { return nil }

func New(ctx context.Context, obj k8sruntime.Object, h framework.Handle) (framework.Plugin, error) {
	ort.SetSharedLibraryPath(LibPath)
	_ = ort.InitializeEnvironment()

	session, err := ort.NewDynamicAdvancedSession(ModelPath, []string{"float_input"}, []string{"variable"}, nil)
	if err != nil { return nil, err }

	client, err := promapi.NewClient(promapi.Config{Address: PromURL})
	if err != nil { return nil, fmt.Errorf("error creating prometheus client: %v", err) }

	return &GreenScore{
		handle:  h,
		session: session,
		promAPI: promv1.NewAPI(client),
	}, nil
}

func main() {
	command := app.NewSchedulerCommand(app.WithPlugin(Name, New))
	logs.InitLogs()
	defer logs.FlushLogs()
	if err := command.Execute(); err != nil {
		fmt.Fprintf(os.Stderr, "%v\n", err)
		os.Exit(1)
	}
}

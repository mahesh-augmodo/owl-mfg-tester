package server

import (
	"bufio"
	"context"
	"fmt"
	"log"
	"os"
	"strings"

	pb "owl_test_agent/proto"
)

type Server struct {
	pb.UnimplementedDutAgentServiceServer

	AgentVersion string
	DeviceId     string
}

func NewServer() *Server {
	agentVersion := "0.1"
	deviceId, err := getCPUInfoSerial()
	if err != nil {
		log.Printf("unable to read deviceID %s", err)
		deviceId = "UNKNOWN"
	}

	return &Server{
		AgentVersion: agentVersion,
		DeviceId:     deviceId,
	}
}

func (s *Server) GetAgentDetails(ctx context.Context, in *pb.GetAgentDetailsRequest) (*pb.GetAgentDetailsResponse, error) {
	log.Printf("Received GetAgentDetails request. Responding with agentVersion: %s and deviceid: %s",
		s.AgentVersion, s.DeviceId)

	return &pb.GetAgentDetailsResponse{
		AgentVersion: s.AgentVersion,
		DeviceId:     s.DeviceId,
	}, nil
}

func getCPUInfoSerial() (string, error) {
	file, err := os.Open("/proc/cpuinfo")
	if err != nil {
		return "", fmt.Errorf("unable to open /proc/cpuinfo %w", err)
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := scanner.Text()
		if strings.HasPrefix(line, "Serial") {
			parts := strings.Split(line, ":")

			if len(parts) > 1 {
				serial := strings.TrimSpace(parts[1])
				return serial, nil
			}
		}
	}

	if err := scanner.Err(); err != nil {
		return "", fmt.Errorf("error reading /proc/cpuinfo %w", err)
	}

	return "", fmt.Errorf("serial not found in /proc/cpuinfo")

}

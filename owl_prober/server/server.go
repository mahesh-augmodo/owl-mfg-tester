package server

import (
	"context"
	"fmt"
	"io"
	"log/slog"
	"os" // For parsing file permissions if needed
	"owl_prober/util"
	"sync"

	pb "owl_prober/proto"

	"google.golang.org/protobuf/types/known/emptypb"
)

type Server struct {
	pb.UnimplementedDutAgentServiceServer

	AgentVersion string
	DeviceId     string
	MacAddr      string
	IPAddr       string

	// Channel to update scrolling text on the OLED, nil if no scrolling is active.
	scrollingTextChan chan<- string
	// Mutex to protect access to scrollingTextChan
	scrollingTextMu sync.Mutex
}

func NewServer() *Server {
	agentVersion := "0.1"
	deviceId, err := util.GetCPUInfoSerial()
	if err != nil {
		slog.Error(fmt.Sprintf("unable to read deviceID %s", err))
		deviceId = ""
	}
	macaddr, ipaddr, err := util.GetWLANMacIp("wlan0")
	if err != nil {
		slog.Error("unable to get MAC address")
		macaddr = ""
	}
	return &Server{
		AgentVersion: agentVersion,
		DeviceId:     deviceId,
		MacAddr:      macaddr,
		IPAddr:       ipaddr,
		// scrollingTextChan and scrollingTextMu are initialized to their zero values (nil and unlocked mutex)
	}
}

func (s *Server) GetAgentDetails(ctx context.Context, in *pb.GetAgentDetailsRequest) (*pb.GetAgentDetailsResponse, error) {
	slog.Debug(fmt.Sprintf("received GetAgentDetails request. Responding with agentVersion: %s, deviceid: %s, macaddr: %s, ipaddr: %s",
		s.AgentVersion, s.DeviceId, s.MacAddr, s.IPAddr))

	return &pb.GetAgentDetailsResponse{
		AgentVersion: s.AgentVersion,
		DeviceId:     s.DeviceId,
		MacAddr:      s.MacAddr,
		IpAddr:       s.IPAddr,
	}, nil
}

func (s *Server) ConfigureOLEDDisplay(ctx context.Context, in *pb.OLEDSettings) (*emptypb.Empty, error) {
	slog.Debug(fmt.Sprintf("received ConfigureOLEDDisplay request with settings: %+v", in))
	if err := util.SetupOLED(in); err != nil {
		slog.Error("failed to setup OLED display", "error", err)
		return nil, err
	}
	slog.Info("OLED display configured successfully")
	return &emptypb.Empty{}, nil
}

func (s *Server) SetOLEDStaticText(ctx context.Context, in *pb.SetOLEDTextRequest) (*emptypb.Empty, error) {
	slog.Debug(fmt.Sprintf("received SetOLEDStaticText request with text: %s", in.Text))

	s.scrollingTextMu.Lock()
	if s.scrollingTextChan != nil {
		// Stop any active scrolling
		slog.Info("Stopping active OLED scrolling text due to SetOLEDStaticText call.")
		s.scrollingTextChan <- "" // Send empty string to signal stop
		s.scrollingTextChan = nil
	}
	s.scrollingTextMu.Unlock()

	if err := util.SetStaticText(in.Text); err != nil {
		slog.Error("failed to set OLED static text", "error", err)
		return nil, err
	}
	slog.Info("OLED static text set successfully")
	return &emptypb.Empty{}, nil
}

func (s *Server) SetOLEDScrollingText(ctx context.Context, in *pb.SetOLEDTextRequest) (*emptypb.Empty, error) {
	slog.Debug(fmt.Sprintf("received SetOLEDScrollingText request with text: %s", in.Text))

	s.scrollingTextMu.Lock()
	defer s.scrollingTextMu.Unlock()

	if s.scrollingTextChan != nil {
		// Update existing scrolling text
		slog.Info("Updating existing OLED scrolling text.", "newText", in.Text)
		s.scrollingTextChan <- in.Text
	} else {
		// Start new scrolling text
		slog.Info("Starting new OLED scrolling text.", "initialText", in.Text)
		updateChan, err := util.SetScrollingText(in.Text)
		if err != nil {
			slog.Error("failed to start OLED scrolling text", "error", err)
			return nil, err
		}
		s.scrollingTextChan = updateChan
	}

	slog.Info("OLED scrolling text command processed successfully")
	return &emptypb.Empty{}, nil
}

func (s *Server) ConfigureBattery(ctx context.Context, in *pb.BatterySettings) (*emptypb.Empty, error) {
	slog.Debug(fmt.Sprintf("received ConfigureBattery request with settings: %+v", in))
	if err := util.SetupBattery(in); err != nil {
		slog.Error("failed to setup battery", "error", err)
		return nil, err
	}
	slog.Info("Battery configured successfully")
	return &emptypb.Empty{}, nil
}

func (s *Server) GetBatteryReadings(ctx context.Context, in *pb.GetBatteryReadingsRequest) (*pb.GetBatteryReadingsResponse, error) {
	slog.Debug("received GetBatteryReadings request")
	resp, err := util.GetBatteryReadings()
	if err != nil {
		slog.Error("failed to get battery readings", "error", err)
		return nil, err
	}
	slog.Debug(fmt.Sprintf("sent GetBatteryReadings response: %+v", resp))
	return resp, nil
}

func (s *Server) DiscoverEventDevices(ctx context.Context, in *pb.DiscoverEventDevicesRequest) (*pb.DiscoverEventDevicesResponse, error) {
	slog.Debug("received DiscoverEventDevices request")
	devices, err := util.DiscoverEventDevices()
	if err != nil {
		slog.Error("failed to discover event devices", "error", err)
		return nil, err
	}
	slog.Debug(fmt.Sprintf("sent DiscoverEventDevices response with %d devices", len(devices)))
	return &pb.DiscoverEventDevicesResponse{Devices: devices}, nil
}

func (s *Server) GetEventReportOverDuration(ctx context.Context, in *pb.GetEventReportOverDurationRequest) (*pb.GetEventReportOverDurationResponse, error) {
	slog.Debug(fmt.Sprintf("received GetEventReportOverDuration request for device %s for %d seconds", in.DevicePath, in.DurationSeconds))
	csvReport, err := util.GetEventReportOverDuration(in.DevicePath, in.DurationSeconds)
	if err != nil {
		slog.Error("failed to get event report over duration", "error", err)
		return nil, err
	}
	slog.Debug("sent GetEventReportOverDuration response")
	return &pb.GetEventReportOverDurationResponse{CsvReport: csvReport}, nil
}

func (s *Server) ConfigureBuzzer(ctx context.Context, in *pb.BuzzerSettings) (*emptypb.Empty, error) {
	slog.Debug(fmt.Sprintf("received ConfigureBuzzer request with settings: %+v", in))
	if err := util.ConfigureBuzzer(in); err != nil {
		slog.Error("failed to configure buzzer", "error", err)
		return nil, err
	}
	slog.Info("Buzzer configured successfully")
	return &emptypb.Empty{}, nil
}

func (s *Server) SetBuzzer(ctx context.Context, in *pb.SetBuzzerRequest) (*emptypb.Empty, error) {
	slog.Debug(fmt.Sprintf("received SetBuzzer request with on: %t", in.On))
	if err := util.SetBuzzer(in.On); err != nil {
		slog.Error("failed to set buzzer state", "error", err)
		return nil, err
	}
	slog.Info("Buzzer state set successfully", "on", in.On)
	return &emptypb.Empty{}, nil
}

func (s *Server) GetSystemState(ctx context.Context, in *pb.GetSystemStateRequest) (*pb.GetSystemStateResponse, error) {
	slog.Debug(fmt.Sprintf("received GetSystemState request with idle_duration_seconds: %d, cpu_temperature_sysfs_path: %s", in.IdleDurationSeconds, in.CpuTemperatureSysfsPath))
	resp, err := util.GetSystemState(in.IdleDurationSeconds, in.CpuTemperatureSysfsPath)
	if err != nil {
		slog.Error("failed to get system state", "error", err)
		return nil, err
	}
	slog.Debug(fmt.Sprintf("sent GetSystemState response: %+v", resp))
	return resp, nil
}

// UploadFile handles client-streaming file uploads.
func (s *Server) UploadFile(stream pb.DutAgentService_UploadFileServer) error {
	var file *os.File
	var filename string
	var totalSize int64
	var receivedSize int64

	slog.Info("Starting file upload stream")

	for {
		req, err := stream.Recv()
		if err == io.EOF {
			break // End of stream
		}
		if err != nil {
			slog.Error("error receiving upload chunk", "error", err)
			return err
		}

		if file == nil { // First chunk, open file
			filename = req.Filename
			totalSize = req.TotalSize
			slog.Info("Receiving file upload", "filename", filename, "totalSize", totalSize)

			file, err = os.Create(filename) // Consider using a secure temp dir or user-specified path
			if err != nil {
				slog.Error("failed to create file for upload", "filename", filename, "error", err)
				return err
			}
			defer file.Close()
		}

		if req.Offset != receivedSize {
			slog.Error("received out-of-order chunk or unexpected offset", "expectedOffset", receivedSize, "receivedOffset", req.Offset)
			return fmt.Errorf("received out-of-order chunk or unexpected offset")
		}

		n, err := file.Write(req.ChunkData)
		if err != nil {
			slog.Error("failed to write chunk to file", "filename", filename, "offset", req.Offset, "error", err)
			return err
		}
		receivedSize += int64(n)

		if receivedSize == totalSize {
			slog.Info("File upload complete", "filename", filename, "receivedSize", receivedSize)
			return stream.SendAndClose(&pb.UploadFileResponse{
				Message: fmt.Sprintf("File %s uploaded successfully", filename),
				Success: true,
			})
		}
	}

	if receivedSize != totalSize {
		slog.Error("file upload incomplete", "filename", filename, "receivedSize", receivedSize, "expectedSize", totalSize)
		return stream.SendAndClose(&pb.UploadFileResponse{
			Message: fmt.Sprintf("File %s upload incomplete", filename),
			Success: false,
		})
	}

	slog.Error("file upload stream ended unexpectedly before completion")
	return fmt.Errorf("file upload stream ended unexpectedly")
}

// DownloadFile handles server-streaming file downloads.
func (s *Server) DownloadFile(req *pb.DownloadFileRequest, stream pb.DutAgentService_DownloadFileServer) error {
	filename := req.Filename
	slog.Info("Starting file download stream", "filename", filename)

	file, err := os.Open(filename)
	if err != nil {
		slog.Error("failed to open file for download", "filename", filename, "error", err)
		return err
	}
	defer file.Close()

	fileInfo, err := file.Stat()
	if err != nil {
		slog.Error("failed to get file info", "filename", filename, "error", err)
		return err
	}
	totalSize := fileInfo.Size()

	buffer := make([]byte, 4096) // Chunk size
	var sentSize int64

	for {
		n, err := file.Read(buffer)
		if err == io.EOF {
			break // End of file
		}
		if err != nil {
			slog.Error("failed to read file chunk", "filename", filename, "error", err)
			return err
		}

		chunkData := buffer[:n]
		resp := &pb.DownloadFileResponse{
			ChunkData: chunkData,
			Offset:    sentSize,
			TotalSize: totalSize,
		}

		if err := stream.Send(resp); err != nil {
			slog.Error("failed to send download chunk", "filename", filename, "offset", sentSize, "error", err)
			return err
		}
		sentSize += int64(n)
	}

	slog.Info("File download complete", "filename", filename, "sentSize", sentSize)
	return nil
}

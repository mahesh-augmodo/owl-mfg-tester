.PHONY: all python go clean proto-python proto-go proto-clean proto owl_prober mfg_tester

PROTO_FILE := proto/test_agent.proto # This is the full path from project root

# Python settings
PYTHON_OUT_DIR := mfg_tester/src/

# Go settings
GO_MODULE_ROOT_DIR := owl_prober
# The full path where the Go files will be generated, derived from go_package option.
# This assumes the go_package option in the .proto file is relative to the GO_MODULE_ROOT_DIR.
GO_GENERATED_DIR := $(GO_MODULE_ROOT_DIR)/proto/

all: mfg_tester owl_prober

proto-python:
	@echo "Compiling Python protobufs..."
	mkdir -p $(PYTHON_OUT_DIR)
	# Remove any existing generated files in the target output path to ensure a clean slate
	python3 -m grpc_tools.protoc -I. \
	  --python_out=$(PYTHON_OUT_DIR) \
	  --pyi_out=$(PYTHON_OUT_DIR) \
	  --grpc_python_out=$(PYTHON_OUT_DIR) \
	  $(PROTO_FILE)
	@echo "Python protobufs compiled to $(PYTHON_OUT_DIR)"

proto-go:
	@echo "Compiling Go protobufs..."
	# Ensure the target directory for Go generated files exists.
	# This path is based on the 'go_package' option in your .proto file.
	mkdir -p $(GO_GENERATED_DIR)
	protoc -I. \
	  --go_out=$(GO_MODULE_ROOT_DIR) --go_opt=paths=source_relative \
	  --go-grpc_out=$(GO_MODULE_ROOT_DIR) --go-grpc_opt=paths=source_relative \
	  $(PROTO_FILE)
	@echo "Go protobufs compiled to $(GO_GENERATED_DIR)"

proto-clean:
	@echo "Cleaning generated files..."
	rm -rf $(PYTHON_OUT_DIR)/*_pb2.py* $(PYTHON_OUT_DIR)/*_grpc.py*
	# Clean Go generated files based on the GO_GENERATED_DIR
	rm -rf $(GO_GENERATED_DIR)/*
	# If the directories are created solely for generated files, they can be removed too
	# rm -rf $(GO_GENERATED_DIR)
	@echo "Cleaned generated protobuf files."

proto: 
	proto-go 
	proto-python

owl_prober:
	make -C owl_prober build

mfg_tester: 
	proto
	owl_prober

clean:
	proto-clean
	make -C owl_prober clean

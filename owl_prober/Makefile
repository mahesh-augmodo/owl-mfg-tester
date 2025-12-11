# Configuration
AGENT_NAME := owl_prober
DEVICE_SERIAL ?= 4dbe780b65b17a32
REMOTE_PATH := /tmp/$(AGENT_NAME)

.PHONY: all build-dev install-dev clean

all: build-dev

# Cross-compile Go app for Linux ARMv7
build-dev:
	@echo "--- Building $(AGENT_NAME) for Linux ARMv7 ---"
	GOOS=linux GOARM=7 GOARCH=arm go build -o dist/$(AGENT_NAME) .

# Build, push, set executable flag, and run binary via ADB shell
# Usage: make install-dev DEVICE_SERIAL=ABCD1234
install-dev: build-dev
	@echo "--- Deploying and Running on $(DEVICE_SERIAL) via ADB ---"
	adb -s $(DEVICE_SERIAL) push dist/$(AGENT_NAME) $(REMOTE_PATH)
	adb -s $(DEVICE_SERIAL) shell chmod +x $(REMOTE_PATH)
	adb -s $(DEVICE_SERIAL) shell $(REMOTE_PATH)

clean:
	@echo "Cleaning build artifacts..."
	rm -rf dist/
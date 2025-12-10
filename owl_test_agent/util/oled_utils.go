package util

import (
	"fmt"
	"image"
	"image/draw"
	"log/slog"
	"strconv"
	"strings"
	"sync"
	"time"
	"unicode/utf8"

	"periph.io/x/conn/v3/gpio"
	"periph.io/x/conn/v3/gpio/gpioreg"
	"periph.io/x/conn/v3/i2c/i2creg"
	"periph.io/x/conn/v3/physic"
	"periph.io/x/devices/v3/ssd1306"
	"periph.io/x/devices/v3/ssd1306/image1bit"
	"periph.io/x/host/v3"

	"golang.org/x/image/font"
	"golang.org/x/image/font/opentype"
	"golang.org/x/image/math/fixed"

	pb "owl_test_agent/proto"
	"owl_test_agent/resources/fonts"
)

// --- Initialization Singleton (Core Refactoring) ---
var (
	// oledHostInitOnce ensures that periph.io host initialization happens only once.
	oledHostInitOnce sync.Once
	// oledDeviceInitOnce ensures that the OLED device itself is initialized only once,
	// unless explicitly reset by SetupOLED for reconfiguration.
	oledDeviceInitOnce sync.Once

	oledDeviceInstance *ssd1306.Dev
	oledInitError      error
)

// InitOLED performs the thread-unsafe hardware initialization steps.
// This function is intended to be called ONLY by oledOnce.Do().
func InitOLED(s *pb.OLEDSettings) (*ssd1306.Dev, error) {

	// Control power and reset pins
	oledPwr := gpioreg.ByName(strconv.Itoa(int(s.PowerPin)))
	oledResetb := gpioreg.ByName(strconv.Itoa(int(s.ResetPin)))
	if oledPwr == nil {
		return nil, fmt.Errorf("OLED reset pin not found pin: %d", s.PowerPin)
	}
	if oledResetb == nil {
		return nil, fmt.Errorf("OLED reset pin not found pin: %d", s.ResetPin)
	}

	oledPwr.Out(gpio.High)
	oledResetb.Out(gpio.Low)
	time.Sleep(50 * time.Millisecond)
	oledResetb.Out(gpio.High)

	// Open I2C bus and set speed
	bus, err := i2creg.Open(s.I2CBusName)
	if err != nil {
		return nil, err
	}
	if err = bus.SetSpeed(physic.KiloHertz * 400); err != nil {
		// This will fail currently. So let's pass
		slog.Error("unable to set i2c speed", "err", err)
	}

	// Initialize SSD1306 device
	opts := ssd1306.DefaultOpts
	opts.W = int(s.Width)
	opts.H = int(s.Height)
	opts.MirrorVertical = true

	dev, err := ssd1306.NewI2C(bus, &opts)
	if err != nil {
		bus.Close()
		return nil, err
	}
	slog.Info("SSD1306 found", "device", dev.String())
	return dev, nil
}

// SetupOLED initializes or re-initializes the OLED device with the provided settings.
// It ensures that periph.io host initialization happens only once.
func SetupOLED(settings *pb.OLEDSettings) error {
	oledHostInitOnce.Do(func() {
		// host.Init() should only be called once per application lifecycle
		if _, err := host.Init(); err != nil {
			slog.Error("failed to initialize periph host", "error", err)
			oledInitError = err // Store the host init error
		}
	})

	// If host.Init() failed, return that error immediately.
	if oledInitError != nil {
		return oledInitError
	}

	// Reset oledDeviceInitOnce to allow re-initialization with new settings.
	// This is done by effectively creating a new sync.Once instance.
	// This ensures that the OLED device can be re-initialized if settings change.
	oledDeviceInitOnce = sync.Once{}
	oledInitError = nil // Clear previous device init error

	oledDeviceInitOnce.Do(func() {
		oledDeviceInstance, oledInitError = InitOLED(settings)
	})

	return oledInitError
}

// GetOLED is the public function to access the initialized OLED device.
// It returns the currently initialized device instance and any error encountered during its setup.
// SetupOLED must be called at least once before calling GetOLED to initialize the device.
func GetOLED() (*ssd1306.Dev, error) {
	return oledDeviceInstance, oledInitError
}

// --- Display Utility Functions ---

// loadFontFace loads a font face with a specified size.
func loadFontFace(fontData []byte, size float64) (font.Face, error) {
	drawFont, err := opentype.Parse(fontData)
	if err != nil {
		return nil, fmt.Errorf("failed to parse font: %w", err)
	}
	return opentype.NewFace(drawFont, &opentype.FaceOptions{
		Size:    size,
		DPI:     100,
		Hinting: font.HintingVertical,
	})
}

// SetStaticText draws a single line of centered text to the OLED and updates the display once.
// Returns an error if the device or font face fails to initialize or write fails.
func SetStaticText(text string) error {
	dev, err := GetOLED()
	if err != nil {
		return err
	}

	face, err := loadFontFace(fonts.ChineseFont, 24) // Use chineseFont for example
	if err != nil {
		return err
	}

	// 1. Initialize buffer and colors
	img := image1bit.NewVerticalLSB(dev.Bounds())
	clearColor := image.NewUniform(image1bit.Off)
	whiteColor := image.NewUniform(image1bit.On)

	// Clear the buffer
	draw.Draw(img, img.Bounds(), clearColor, image.Point{}, draw.Src)

	// 2. Calculate text metrics for centering
	metrics := face.Metrics()
	textWidth := font.MeasureString(face, text)

	// Calculate (x, y) coordinates for center alignment
	// X: Horizontal center
	x := fixed.I(dev.Bounds().Dx()/2) - textWidth/2
	// Y: Vertical center (adjusting for font ascent/descent)
	y := fixed.I(dev.Bounds().Dy()/2) + metrics.Ascent - metrics.Height/2

	// 3. Draw the string
	drawer := font.Drawer{
		Dst:  img,
		Src:  whiteColor,
		Face: face,
		Dot:  fixed.Point26_6{X: x, Y: y},
	}
	drawer.DrawString(text)

	// 4. Update the device display
	if _, err := dev.Write(img.Pix); err != nil {
		slog.Error("Error during OLED device write.")
		return err
	}
	return nil
}

// SetScrollingText starts a goroutine to continuously draw and scroll text on the OLED.
// It returns a channel that can be used to update the scrolling text, and an error if initialization fails.
// Send an empty string ("") to the update channel to stop the scrolling.
func SetScrollingText(initialText string) (chan<- string, error) {
	dev, err := GetOLED()
	if err != nil {
		return nil, err
	}

	face, err := loadFontFace(fonts.ChineseFont, 24)
	if err != nil {
		return nil, err
	}

	// 1. INITIALIZE BUFFER AND COLORS ONCE
	img := image1bit.NewVerticalLSB(dev.Bounds())
	clearColor := image.NewUniform(image1bit.Off)
	whiteColor := image.NewUniform(image1bit.On)

	textY := fixed.I(dev.Bounds().Dy()/2) + face.Metrics().Descent // Vertical position

	// Create a channel for text updates
	textUpdateChan := make(chan string)
	// Create a channel to signal stopping the goroutine
	stopChan := make(chan struct{})

	// Local function to prepare the scrolling text string
	prepareScrollingText := func(txt string) (fixed.Int26_6, string) {
		gap := strings.Repeat(" ", max(2, utf8.RuneCountInString(txt)/2))
		scrollingText := txt + gap
		scrollResetDistance := font.MeasureString(face, scrollingText)
		scrollingText = scrollingText + txt // Double the text for continuous loop
		return scrollResetDistance, scrollingText
	}

	scrollingText := initialText
	scrollResetDistance, preparedScrollingText := prepareScrollingText(scrollingText)
	scrollOffset := fixed.I(dev.Bounds().Dx())

	go func() {
		defer close(stopChan) // Ensure stopChan is closed when goroutine exits

		const targetFrameRate = 12
		targetFrameTime := time.Second / time.Duration(targetFrameRate)

		drawer := font.Drawer{
			Dst:  img,
			Src:  whiteColor,
			Face: face,
		}

		for { // Infinite Loop
			select {
			case newText := <-textUpdateChan:
				if newText == "" { // Signal to stop scrolling
					slog.Info("Stopping OLED scrolling text goroutine.")
					// Clear display on stop
					draw.Draw(img, img.Bounds(), clearColor, image.Point{}, draw.Src)
					dev.Write(img.Pix)
					return // Exit goroutine
				}
				slog.Info("Updating OLED scrolling text", "newText", newText)
				scrollingText = newText
				scrollResetDistance, preparedScrollingText = prepareScrollingText(scrollingText)
				scrollOffset = fixed.I(dev.Bounds().Dx()) // Reset scroll position for new text
				drawer.Dot.X = scrollOffset // Reset drawer position
			case <-time.After(targetFrameTime):
				renderStartTime := time.Now()
				
				scrollOffset -= fixed.I(5) // Move 5 units (1 full pixel)

				if scrollOffset < -scrollResetDistance {
					scrollOffset = fixed.I(0)
				}

				draw.Draw(img, img.Bounds(), clearColor, image.Point{}, draw.Src)

				// Update drawer position and draw
				drawer.Dot.X = scrollOffset
				drawer.Dot.Y = textY
				drawer.DrawString(preparedScrollingText)
				if _, err := dev.Write(img.Pix); err != nil {
					slog.Error("Error during device write in scroll loop:", "error", err)
					return // Exit goroutine on write error
				}

				// Frame rate control
				elapsedTime := time.Since(renderStartTime)
				if elapsedTime < targetFrameTime {
					time.Sleep(targetFrameTime - elapsedTime)
				} else {
					slog.Warn("Frame rendering took too long", "elapsedtime", elapsedTime)
					// Optionally drop or adjust scroll speed to compensate
				}
			}
		}
	}()
	return textUpdateChan, nil
}

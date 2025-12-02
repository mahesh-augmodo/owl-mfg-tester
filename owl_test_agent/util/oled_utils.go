package util

import (
	"fmt"
	"image"
	"log"
	"log/slog"
	"strconv"
	"time"

	"periph.io/x/conn/v3/gpio"
	"periph.io/x/conn/v3/gpio/gpioreg"
	"periph.io/x/conn/v3/i2c/i2creg"
	"periph.io/x/devices/v3/ssd1306"
	"periph.io/x/devices/v3/ssd1306/image1bit"
	"periph.io/x/host/v3"

	"golang.org/x/image/font"
	"golang.org/x/image/font/gofont/goregular"
	"golang.org/x/image/font/opentype"
	"golang.org/x/image/math/fixed"
)

type oledDevice struct {
	I2CBus   uint8
	DevAddr  uint8
	Height   int
	Width    int
	PowerPin int
	ResetPin int
}

func SetupOLED() {
	if _, err := host.Init(); err != nil {
		slog.Error(err.Error())
	}

	var oled oledDevice
	oled.I2CBus = 2
	oled.DevAddr = 0x3C
	oled.Width = 128
	oled.Height = 64
	oled.PowerPin = 17
	oled.ResetPin = 187

	// Use i2c-reg to find available I2C bus
	bus, err := i2creg.Open("/dev/i2c-2")
	if err != nil {
		slog.Error(err.Error())
	}
	defer bus.Close()
	opts := ssd1306.DefaultOpts
	opts.W = oled.Width
	opts.H = oled.Height
	opts.MirrorVertical = true
	opts.Sequential = false

	// First enable power and reset to OLED module
	oled_pwr := gpioreg.ByName(strconv.Itoa(oled.PowerPin))
	if oled_pwr == nil {
		slog.Error("unable to find OLED power pin")
	}
	oled_resetb := gpioreg.ByName(strconv.Itoa(oled.ResetPin))
	if oled_resetb == nil {
		slog.Error("unable to find OLED reset pin")
	}

	oled_pwr.Out(gpio.High)
	oled_resetb.Out(gpio.Low)
	time.Sleep(25 * time.Millisecond)
	oled_resetb.Out(gpio.High)
	dev, err := ssd1306.NewI2C(bus, &opts)
	if err != nil {
		slog.Error("failed to initialize SSD1306 OLED controller")
		slog.Error(err.Error())
	}
	slog.Info(fmt.Sprintf("Device = %s", dev.String()))

	// Draw on it.
	img := image1bit.NewVerticalLSB(dev.Bounds())
	draw_font, err := opentype.Parse(goregular.TTF)
	if err != nil {
		slog.Error("failed to parse font", "err", err)
		return
	}
	face, err := opentype.NewFace(draw_font, &opentype.FaceOptions{
		Size:    20,
		DPI:     72,
		Hinting: font.HintingFull,
	})
	drawer := font.Drawer{
		Dst: img,
		Src: &image.Uniform{image1bit.On},

		Face: face,
		Dot:  fixed.P(0, 36),
	}

	// Draw the text onto the image buffer
	drawer.DrawString("BAT CHG Test")

	// The previous rectangle drawing code is removed here.

	// Send the image buffer (containing only the text) to the OLED display
	if err := dev.Draw(dev.Bounds(), img, image.Point{}); err != nil {
		log.Fatal(err)
	}
	time.Sleep(15 * time.Second)
	dev.Halt()
}

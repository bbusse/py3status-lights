"""
Control LED lights.

Configuration parameters:
    name: The name of the light source
    host: The host to connect to (default 'localhost')
    port: The port to use (default 2342)
    proto: The protocol to use (default 'rgb')
    leds_total: The total number of LEDs (default: 100)
    mode: The mode to operate LEDs in (default: 'default')
    colors: The list of pre-defined colors to cycle through
    color_picker: A color picker executable (default: ['color_picker'])
    format: The display format for this module (default 'lights')

Format placeholders:
    {name} The name of the light source
    {color} The color to set
    {icon} A module icon
    {icon_color} An icon showing the color of the light source
    {leds} The number of LEDs to set

Color options:
    color: Default to color_good, active color otherwise

@author bbusse, Björn Busse

SAMPLE OUTPUT
{"full_text": "\ud83d\udca1 lounge 23 \u25cf #E05B22", \
"instance": "lounge 0", "name": "lounge", "color": "#E05B22"}
"""

import socket
import subprocess


class Py3status:
    """ """

    # Configuration parameters
    name = "light"
    host = "localhost"
    port = 2342
    proto = "rgb"
    leds_total = 100
    mode = "default"
    colors = ["#68D74C", "#E05B22", "#C60D12"]
    color_picker = ["color_picker"]
    icon = "💡"
    icon_color = "●"
    format = "{icon} {name} {leds} {icon_color} {color}"

    def post_config_hook(self):
        self.ncolors = len(self.colors)
        self.leds = self.py3.storage_get("leds")
        self.color = self.py3.storage_get("color")
        self.color_idx = self.py3.storage_get("color_idx")

        # Nothing in storage: Set initial number of LEDs
        if not self.leds:
            self.py3.log(
                "Storage empty, setting initial values", self.py3.LOG_WARNING
            )
            self.leds = 23

        # Set initial color index to first element
        if not self.color_idx:
            self.color_idx = 0

        # Set intial color to COLOR_GOOD
        if not self.color:
            self.color = self.py3.COLOR_GOOD

        self._get_socket()

    def lights(self):
        name = self.name
        color = self.color
        icon = self.icon
        icon_color = self.icon_color
        leds = self.leds

        return {
            "full_text": self.py3.safe_format(
                self.format, {"name": name}, {"color": color}, {"leds": leds}
            ),
            "name": name,
            "color": color,
            "icon": icon,
            "icon_color": icon_color,
            "leds": leds,
        }

    def on_click(self, event):
        """
        Control light state
        """

        # Left mouse button: Turn on lights or switch color
        if event["button"] == 1:
            self.color_idx += 1
            if self.color_idx > self.ncolors - 1:
                self.color_idx = 0

            self.color = self.colors[self.color_idx]
            self._send_frame()

        # Middle mouse button: Open color widget
        elif event["button"] == 2:
            for c in self._run_color_picker(self.color_picker):
                self.color = c.rstrip("\n")
                self.py3.log(self.color, self.py3.LOG_INFO)
                self._send_frame()
                self.py3.update()

        # Right mouse button: Turn off
        elif event["button"] == 3:
            self.color = "000000"
            self._send_frame()
            self.color = self.py3.COLOR_GOOD

        # Scroll up: Increase number of LEDs
        elif event["button"] == 4:
            if self.leds < self.leds_total:
                self.leds += 1
                self._send_frame()

        # Scroll down: Decrease number of LEDs
        elif event["button"] == 5:
            if self.leds > 0:
                self.leds -= 1
                self._send_frame()

        self._store_state()

    def _store_state(self):
        """
        Store module state
        """
        self.py3.storage_set("leds", self.leds)
        self.py3.storage_set("color", self.color)
        self.py3.storage_set("color_idx", self.color_idx)

    def _get_socket(self):
        """
        Bind socket
        """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            self.sock.sendto("".encode, (self.host, self.port))
        except socket.gaierror:
            self.py3.log("Failed to bind v4 socket", self.py3.LOG_WARNING)
            self.sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        except Exception as e:
            self.py3.log("Socket error: " + str(e), self.py3.LOG_ERROR)
            return False

    def _header(self, proto):
        header = ""

        if proto == "drgb":
            # protocol
            header += "02"
            # no timeout
            header += "FF"

        return header

    def _frame(self, proto, leds, leds_total, color):
        """
        Compose message to send
        """
        frame = self._header(proto)
        start = 0

        if self.mode == "center":
            start = int((leds_total - leds) / 2)

        if self.mode == "center" or self.mode == "default":
            for n in range(leds_total):
                if n >= start and n < start + leds:
                    frame += color
                else:
                    frame += "000000"

        elif self.mode == "distribute":
            if leds < 1:
                return

            m = int(leds_total / leds)

            for n in range(leds_total):
                if n % m == 1 or m < 2:
                    frame += color
                else:
                    frame += "000000"

        return frame

    def _send_frame(self):
        """
        Send UDP message
        """
        msg = self._frame(self.proto, self.leds, self.leds_total, self.color)

        try:
            self.sock.sendto(bytes.fromhex(msg), (self.host, self.port))
        except Exception as e:
            self.py3.log(
                "Failed to contact light: " + str(e), self.py3.LOG_ERROR
            )

    def _run_color_picker(self, cmd):
        """
        Run a color picker as external command
        """
        ps = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, universal_newlines=True
        )

        for stdout_line in iter(ps.stdout.readline, ""):
            yield stdout_line

        ps.stdout.close()
        ps.wait()


if __name__ == "__main__":
    """
    Run module in test mode.
    """
    from py3status.module_test import module_test

    module_test(Py3status)

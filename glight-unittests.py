import unittest
import glight
import logging

# Usage: python -m glight-unittests

class TestGlightClientMethods(unittest.TestCase):

    def setUp(self):
        self.device = glight.G213()
        self.device_name = self.device.device_name_short
        self.test_colors = ["ffffff", "ff0000", "00ff00", "0000ff", "ff00ff"]
        self.test_brightnesses = [0, 20, 40, 60, 80, 100]
        self.test_speeds = [1000, 2000, 4000]
        self.logger = logging.getLogger()

    def test_client(self):
        client = glight.GlightClient()
        client.connect()
        self.run_set_color_at_test(client)
        self.run_set_colors_test(client)
        self.run_set_breathe_test(client)
        self.run_set_cycle_test(client)

    def test_controller(self):
        controller = glight.GlightController(glight.GlightController.BACKEND_DBUS)
        self.run_set_color_at_test(controller)
        self.run_set_colors_test(controller)
        self.run_set_breathe_test(controller)
        self.run_set_cycle_test(controller)

    def run_set_color_at_test(self, client):
        self.assertIsNotNone(client)
        client.save_state()

        for field in range(0, self.device.max_color_fields):
            for color in self.test_colors:
                client.set_color_at(self.device_name, color, field)
                self.logger.info("set_color_at({}, {}, {})"
                                 .format(self.device_name, color, field))

        client.load_state()

    def run_set_colors_test(self, client):
        self.assertIsNotNone(client)
        client.save_state()

        client.set_colors(self.device_name, self.test_colors)
        self.logger.info("set_colors({}, {})"
                         .format(self.device_name, self.test_colors))

        client.load_state()

    def run_set_breathe_test(self, client):
        self.assertIsNotNone(client)
        client.save_state()

        for color in self.test_colors:
            for speed in self.test_speeds:
                for brightness in self.test_brightnesses:
                    client.set_breathe(self.device_name, color, speed, brightness)
                    self.logger.info("set_breathe({}, {}, {}, {})"
                                     .format(self.device_name, color, speed, brightness))

        client.load_state()

    def run_set_cycle_test(self, client):
        self.assertIsNotNone(client)
        client.save_state()

        for speed in self.test_speeds:
            for brightness in self.test_brightnesses:
                client.set_cycle(self.device_name, speed, brightness)
                self.logger.info("set_cycle({}, {}, {})"
                                 .format(self.device_name, speed, brightness))

        client.load_state()

    # def test_split(self):
    #     s = 'hello world'
    #     self.assertEqual(s.split(), ['hello', 'world'])
    #     # check that s.split fails when the separator is not a string
    #     with self.assertRaises(TypeError):
    #         s.split(2)

if __name__ == '__main__':
    unittest.main()
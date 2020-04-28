import unittest
from time import sleep
from subprocess import run
from src.Socket_Singleton import Socket_Singleton, MultipleSingletonsError


class TestMain(unittest.TestCase):
    def setUp(self):
        self.app = Socket_Singleton()
        self.traced_args = []


    def test_defaults(self):
        result = run("test_app.py defaults", shell=True, capture_output=True)
        self.assertFalse(result.stdout)


    def test_different_port(self):
        result = run("test_app.py different_port", shell=True, capture_output=True)
        self.assertTrue(result.stdout)

    
    def test_no_client(self):
        result = run("test_app.py no_client foo bar baz", shell=True, capture_output=True)
        self.assertNotIn("noclient", self.app.arguments)
        self.assertNotIn("foo", self.app.arguments)
        self.assertNotIn("bar", self.app.arguments)
        self.assertNotIn("baz", self.app.arguments)
        

    def test_client(self):
        run("test_app.py defaults foo bar baz", shell=True, capture_output=True)
        self.assertIn("defaults", self.app.arguments)
        self.assertIn("foo", self.app.arguments)
        self.assertIn("bar", self.app.arguments)
        self.assertIn("baz", self.app.arguments)


    def test_context(self):
        result = run("test_app.py context", shell=True, capture_output=True)
        self.assertFalse(result.stdout)


    def test_context_no_strict(self):
        result = run("test_app.py context_no_strict", shell=True, capture_output=True)
        self.assertEqual(result.stdout.decode("UTF-8"), "MultipleSingletonsError\r\n")


    def test_no_strict(self):
        result = run("test_app.py no_strict", shell=True, capture_output=True)
        self.assertEqual(result.stdout.decode("UTF-8"), "MultipleSingletonsError\r\n")


    def test_trace(self):
        self.app.trace(self.traced)
        run("test_app.py defaults foo bar baz", shell=True, capture_output=True)
        self.assertEqual(len(self.traced_args), 4)


    def test_untrace(self):
        self.app.trace(self.traced)
        run("test_app.py defaults foo bar baz", shell=True, capture_output=True)
        self.app.untrace(self.traced)
        run("test_app.py defaults foo bar baz", shell=True, capture_output=True)
        self.assertEqual(len(self.traced_args), 4)


    def traced(self, argument):
        self.traced_args.append(argument)


    def test_slam_args(self):
        self.app.arguments.clear()
        for i in range(10):
            run("test_app.py defaults foo bar bin baz", shell=True)

        self.assertEqual(len(self.app.arguments), 50)


    def tearDown(self):
        self.app.close()
        sleep(1)


if __name__ == "__main__":
    unittest.main()

import base64
import json
import unittest

from tplink_m7350.client import M7350AuthError, M7350Client
from tplink_m7350.codec import Base64JsonCodec


class CodecTests(unittest.TestCase):
    def test_base64_codec_encodes_like_router_javascript(self):
        codec = Base64JsonCodec()

        encoded = json.loads(codec.encode({"module": "authenticator", "action": 0}))

        self.assertEqual(
            json.loads(base64.b64decode(encoded["data"])),
            {"module": "authenticator", "action": 0},
        )

    def test_base64_codec_decodes_wrapped_response(self):
        codec = Base64JsonCodec()
        body = base64.b64encode(b'{"result":0,"token":"abc"}').decode()

        self.assertEqual(codec.decode(json.dumps({"data": body})), {"result": 0, "token": "abc"})

    def test_authenticated_call_requires_token(self):
        client = M7350Client()

        with self.assertRaises(M7350AuthError):
            client.call("webServer", 0)


if __name__ == "__main__":
    unittest.main()

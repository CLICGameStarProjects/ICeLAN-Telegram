import argparse
import base64

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("username")

    args = parser.parse_args()

    keys = dict(line.split(",") for line in open(".keys", "r").read().splitlines())

    payload = str(base64.b64encode((args.username + " " + keys["code"]).encode("utf-8")), "utf-8")

    print(f"tg://resolve?domain=icelanim_bot&start={payload}")

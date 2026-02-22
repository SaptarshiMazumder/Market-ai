import runpod


def handler(job):
    print("Hello World")
    return {"message": "Hello World"}


runpod.serverless.start({"handler": handler})

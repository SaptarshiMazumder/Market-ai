import requests
import json

def run_editorial_job():
    # API Configuration
    url = "https://api.runpod.ai/v2/1dv4vwaqf3quge/run"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer rpa_S6NYJWCZI6VL3RCDCMFPM6MYPN9B07BVWFZUUCMZ19k01v"
    }

    # The exact prompt provided
    prompt_text = (
        "A young Asian woman, early 20s, stands in a derelict urban alley. Her skin micro-texture is visible under the harsh flash: pores slightly enlarged from the heat, subtle sub-surface scattering around her cheekbones, a scattering of faint freckles across her nose. Fine peach fuzz is illuminated along her jawline. Her fingernails are short, square-shaped with a high-gloss clear coat, cuticles neatly maintained. Black, choppy bob, individual flyaway strands catching the light, slight scalp visibility near the crown.She wears high-waisted denim shorts. The weave density of the denim is tight, with visible indigo dye variations. Oxidized patina on the brass button closure. Frayed threads at the hem. A thick, faux fur bomber jacket in a muted olive green. The way light hits the individual fibers of the faux fur creates a subtle halo effect. She leans against a damp concrete slab with hairline fractures, efflorescence mineral deposits, and a single rusted 10mm bolt protruding from the upper left. The time is late afternoon, the angle of incidental light suggesting a low sun, motes of dust suspended in the air. She holds a disposable camera in her right hand, her thumb resting on the flash button. Fingerprints smudge the plastic casing. The weight of the camera subtly pulls on the fabric of her jacket sleeve. The camera’s plastic reflects a distorted version of her skin tone. Medium-shot on a 35mm cinematic prime lens, hard on-camera flash with 0.5 EV compensation, lo-fi candid fashion editorial mood, desaturated, muted urban tones."
    )

    # Payload structure matching your handler.py requirements
    payload = {
        "input": {
            "prompt": prompt_text
        }
    }

    # Execute the request
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        print(f"✅ Job Queued Successfully!")
        print(f"Job ID: {result.get('id')}")
        print(f"Status: {result.get('status')}")
        
    except requests.exceptions.HTTPError as err:
        print(f"❌ API Error: {err.response.text}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    run_editorial_job()

# import requests

# xml = """
# <?xml version='1.0' encoding='UTF-8'?>
# <mainbody>
#    <header>
#        <usercode>0000000000</usercode>
#        <password>FAKE_NETGSM_PASSWORD</password>
#        <startdate>290420250900</startdate>        
#        <stopdate>290420251900</stopdate>
#    </header>
# </mainbody>"""
# headers = {'Content-Type': 'application/xml'}
# print(requests.post('https://api.netgsm.com.tr/netsantral/statistics', data=xml, headers=headers).text)

import whisperx


audio_path = "3.wav"

device = "cpu"
print("Model yükleniyor...")
model = whisperx.load_model("large-v2", device=device, compute_type="int8")  # CPU için ideal

audio = whisperx.load_audio(audio_path)
result = model.transcribe(audio)

print("\n--- Türkçe Transcript ---\n")
for seg in result["segments"]:
    print(f"{seg['start']:.2f}-{seg['end']:.2f}: {seg['text']}")

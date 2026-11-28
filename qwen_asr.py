"""Opt-in, offline Qwen speech recognition for local audio."""

import argparse
import subprocess
from pathlib import Path


class QwenASR:
    def __init__(self, processor, model):
        self.processor = processor
        self.model = model

    def transcribe(self, audio, language=None, *, fp16=False):
        import torch

        if isinstance(audio, (str, Path)):
            path = Path(audio).expanduser()
            if not path.is_file():
                raise ValueError('An existing local audio file is required.')
            import numpy as np

            pcm = subprocess.run(
                ['ffmpeg', '-nostdin', '-v', 'error', '-protocol_whitelist', 'file,pipe',
                 '-i', str(path.resolve()), '-vn', '-ac', '1', '-ar', '16000', '-f', 'f32le', 'pipe:1'],
                check=True, stdout=subprocess.PIPE, timeout=30,
            ).stdout
            audio = np.frombuffer(pcm, dtype='<f4').copy()
        inputs = self.processor.apply_transcription_request(audio=audio, language=language)
        inputs = inputs.to(self.model.device, self.model.dtype)
        with torch.inference_mode():
            tokens = self.model.generate(**inputs, max_new_tokens=256)
        text = self.processor.decode(tokens[:, inputs['input_ids'].shape[1]:],
                                     return_format='transcription_only')[0]
        return {'text': text.strip()}


def load_qwen_model(model_path):
    path = Path(model_path).expanduser()
    if not (path / 'model.safetensors').is_file():
        raise ValueError('Qwen model weights not found in the local directory.')
    from transformers import AutoModelForMultimodalLM, AutoProcessor

    processor = AutoProcessor.from_pretrained(path, local_files_only=True, trust_remote_code=False)
    model = AutoModelForMultimodalLM.from_pretrained(path, local_files_only=True,
                                                   trust_remote_code=False, dtype='auto')
    return QwenASR(processor, model.eval())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('audio', type=Path)
    parser.add_argument('--model', type=Path, default=Path.home() / 'models' / 'Qwen3-ASR-1.7B-hf')
    parser.add_argument('--language', default='de')
    parser.add_argument('--threads', type=int, choices=range(1, 9), default=2)
    args = parser.parse_args()
    if not args.audio.is_file():
        parser.error('audio must be an existing local file')
    import torch

    torch.set_num_threads(args.threads)
    model = load_qwen_model(args.model)
    print(model.transcribe(args.audio, args.language)['text'])


if __name__ == '__main__':
    main()

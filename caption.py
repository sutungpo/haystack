import torch
import librosa
import numpy as np
from pathlib import Path
from transformers import pipeline
from datasets import Dataset
from torch.utils.data import DataLoader
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

SAMPLE_RATE = 16000

def collate_fn(batch):
    pass

class ASRInference:
    def __init__(self, model_id: str = None, model_path: str = None, batch_size: int = 16):
        self.model_id = model_id
        self.model_path = model_path
        self.batch_size = batch_size
        self.pipe, self.generate_kwargs = self._load_model()
        
    def _load_model(self):
        model = self.model_id if self.model_id is not None else self.model_path
        pipe = pipeline(
            "automatic-speech-recognition",
            model=model,
            device="cuda",
            torch_dtype=torch.float16,
            chunk_length_s=30.0,
            batch_size=self.batch_size,
        )
        generate_kwargs = {
            "language": "Japanese",
            "no_repeat_ngram_size": 0,
            "repetition_penalty": 1.0, 
        }
        return pipe, generate_kwargs
    
    def _data_generator(self, audio: str|Path, vad_segments: str|Path):
        # extract audio segments from vad segments file, each segment contains 'start_time' and 'end_time', then yield the segment.
        audio, vad_segments = Path(audio), Path(vad_segments)
        if not audio.exists() or not vad_segments.exists():
            return
        audio, _ = librosa.load(audio, sr=SAMPLE_RATE)
        vad_segments = vad_segments.read_text(encoding='utf-8').splitlines()
        for segment in vad_segments:
            start_time, end_time = map(float, segment.split('\t')[:2])
            start_slice, end_slice = int(start_time*SAMPLE_RATE), int(end_time*SAMPLE_RATE)
            if end_slice > len(audio):
                end_slice = len(audio)
            # "When passing a dictionary to AutomaticSpeechRecognitionPipeline, the dict needs to contain a "raw" key containing the numpy array representing the audio and a "sampling_rate" key, containing the sampling_rate associated with that array" 
            yield {'raw': audio[start_slice:end_slice], 'sampling_rate': SAMPLE_RATE, 'start_time':start_time, 'end_time':end_time}
    def inference(self, audio: str|Path, vad_segments: str|Path):
        audio, vad_segments = Path(audio), Path(vad_segments)
        if not audio.exists() or not vad_segments.exists():
            return
        raw_dataset = Dataset.from_generator(self._data_generator, gen_kwargs={"audio": audio, "vad_segments": vad_segments})
        dataset = raw_dataset.select_columns(['raw', 'sampling_rate'])
        dataset = dataset.with_format("numpy")
        dataloader = DataLoader(dataset, batch_size=self.batch_size, shuffle=False, num_workers=0, collate_fn=lambda x: x)
        texts = []
        for batch in dataloader:
            result = self.pipe(batch, generate_kwargs=self.generate_kwargs)
            texts.extend(result)
        final_result = [{"start_time": raw_dataset[i]['start_time'], "end_time": raw_dataset[i]['end_time'], **item} for i, item in enumerate(texts) if i < len(raw_dataset)]
        return final_result
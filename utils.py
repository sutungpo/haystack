# *-* coding: utf-8 *-*
from logging import getLogger, basicConfig, DEBUG
import regex as re
basicConfig(level=DEBUG)
logger = getLogger(__name__)    

import pandas as pd
from pathlib import Path
def metadata_csv(dataset_path: str | Path):
    """
    Generate metadata.csv for dataset with pandas
    Dataset could be loaded by datasets.load_dataset function, it could directly load audio files as following structure with default columns  ['audio', 'label']
        1. default csv file name is metadata.csv, it will use AudioFolder with metadata method, recommended.
        2. For customized columns, the metadata.csv should be in the same folder with audio files, for customized-name csv file, use `load_dataset('csv', data_files={'train': 'train.csv', 'test': 'test.csv'})`
        3. other optional load methods: Dataset.from_dict({"audio": ["path/to/audio_1"]}).cast_column("audio", Audio()) or Dataset.from_pandas(df).cast_column("audio", Audio())
    dataset_path
    |-- test
    |   |-- metadata.csv // optional
    |   |-- audio1.mp3
    |   |-- audio2.mp3
    |   |-- ...
    |-- train
    |   |-- metadata.csv // optional
    |   |-- audio3.mp3
    |   |-- audio4.mp3
    |   |-- ...
    """
    dataset_path = Path(dataset_path)
    if not dataset_path.exists():
        return
    
    metadatas = []
    texts = []
    for audio in dataset_path.glob('*.mp3'):
        text = audio.with_suffix('.txt')
        if not text.exists():
            continue
        content = text.read_text(encoding='utf-8')
        metadatas.append((f"'{audio.name}'", f"'{content}'"))
        text.unlink()
    pd.DataFrame(metadatas, columns=['file_name', 'sentence']).to_csv(dataset_path / 'metadata.csv', index=False)

def voice_detection(audio : str | Path):
    """
    Detect voice in audio file, return the detected voice ranges in txt format, each line contains start, end timestamps, labels.
    """
    audio = Path(audio)
    if not audio.exists():
        return
    try:
        from pyannote.audio import Pipeline
    except Exception as e:
        logger.error(e)
        return
    MAX_LENGTH = 25.0
    MAX_GAP = 6.0
    label_txt = audio.with_suffix('.txt')
    initial_segments = []
    pipeline = Pipeline.from_pretrained("pyannote/voice-activity-detection")
    output = pipeline(audio)
    for segment in output.get_timeline().support():
        initial_segments.append(segment)
    if len(initial_segments) == 0:
        return
    start_time = initial_segments[0].start
    end_time = initial_segments[0].end
    final_segments = []
    for segment in initial_segments[1:]:
        if segment.start - end_time > MAX_GAP or segment.end - start_time > MAX_LENGTH:
            final_segments.append((start_time, end_time))
            start_time = segment.start
            end_time = segment.end
        else:
            end_time = segment.end
    final_segments.append((start_time, end_time))
    with open(label_txt, 'a', encoding='utf-8') as f:
        for i, (start, end) in enumerate(final_segments, 1):
            f.write(f'{start:.2f}\t{end:.2f}\t{label_txt.stem}_{i}\n')

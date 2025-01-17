from pydantic import BaseModel


class AnswerEncryption(BaseModel):
    batch_limit: int = 1000
    max_retries: int = 5
    retry_timeout: int = 12 * 60 * 60


class AudioFileConvert(BaseModel):
    command: str = "ffmpeg -i {fin} -vn -ar 44100 -ac 2 -b:a 192k {fout}"
    subprocess_timeout: int = 60  # sec
    task_wait_timeout: int = 30  # sec


class ImageConvert(BaseModel):
    command: str = "convert -strip -interlace JPEG -sampling-factor 4:2:0 -quality 85 -colorspace RGB {fin} {fout}"
    subprocess_timeout: int = 20  # sec
    task_wait_timeout: int = 10  # sec

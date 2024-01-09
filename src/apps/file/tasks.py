import os
import subprocess

from broker import broker
from config import settings
from infrastructure.logger import logger


def generate_command(fin: str, fout: str):

    return settings.task_audio_file_convert.command.format(fin=fin, fout=fout)


@broker.task()
async def convert_audio_file(filename: str, remove_src: bool = True) -> str:
    LOG_PREFIX = "convert_audio_file: "

    out_filename = filename + ".mp3"
    fin = settings.uploads_dir / filename
    fout = settings.uploads_dir / out_filename

    logger.info(f"{LOG_PREFIX}In: {fin}")

    try:
        cmd = generate_command(fin, fout)

        logger.info(f"{LOG_PREFIX}Run `{cmd}`")
        subprocess.check_output(
            cmd,
            stderr=subprocess.STDOUT,
            shell=True,
            timeout=settings.task_audio_file_convert.subprocess_timeout,
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"{LOG_PREFIX}Convertion error: {fin} => {fout}")
        raise Exception(f"{LOG_PREFIX}Error message: {e.output.decode()}")
    finally:
        if remove_src:
            os.remove(fin)

    logger.info(f"{LOG_PREFIX}Out: {fout}")

    return out_filename

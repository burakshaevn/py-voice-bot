"""Сервис для генерации голосовых сообщений."""

import io
import logging
import re
import wave
from pathlib import Path
from typing import Optional

from piper import PiperVoice, SynthesisConfig

try:
    from pydub import AudioSegment
    from pydub.effects import normalize
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    AudioSegment = None  # type: ignore
    normalize = None  # type: ignore

logger = logging.getLogger(__name__)


class VoiceService:
    """Сервис для генерации голосовых сообщений."""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Инициализация сервиса генерации голоса.
        
        :param model_path: Путь к модели .onnx. Если None, используется модель по умолчанию.
        """
        try:
            if model_path is None:
                # Используем русскую модель из piper1-gpl
                model_path = Path(__file__).parent.parent / "piper1-gpl" / "ru_RU-ruslan-medium.onnx"
            
            model_path = Path(model_path)
            if not model_path.exists():
                raise FileNotFoundError(f"Модель не найдена: {model_path}")
            
            self.voice = PiperVoice.load(str(model_path))
            # Настройки для более низкого и брутального голоса без шумов
            self.syn_config = SynthesisConfig(
                volume=1.0,
                length_scale=1.2,  # Медленнее = более низкий голос
                noise_scale=0.1,  # Минимальный шум для чистого звука
                noise_w_scale=0.1,  # Минимальная вариативность для стабильного голоса
                normalize_audio=True,
            )
            logger.info("Сервис генерации голоса успешно инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации генератора голоса: {e}")
            raise
    
    @staticmethod
    def process_pauses(text: str) -> str:
        """
        Обрабатывает паузы в тексте.
        
        Поддерживаемые форматы:
        - | или |1 - короткая пауза (запятая)
        - || или |2 - средняя пауза (точка с запятой)
        - ||| или |3 - длинная пауза (точка)
        - |0.5| - пауза с указанием секунд (например, |0.5| = 0.5 секунды)
        - <break time="0.5s"/> - SSML-подобный формат
        
        :param text: Текст с маркерами пауз
        :return: Текст с обработанными паузами
        """
        # Обрабатываем SSML-подобный формат: <break time="Xs"/>
        def replace_break(match):
            time_str = match.group(1)
            try:
                seconds = float(time_str.rstrip('s'))
                if seconds <= 0.3:
                    return ', '
                elif seconds <= 0.7:
                    return '; '
                else:
                    return '. '
            except ValueError:
                return ', '
        
        text = re.sub(r'<break\s+time=["\']?(\d+\.?\d*)\s*s["\']?\s*/>', replace_break, text, flags=re.IGNORECASE)
        
        # Обрабатываем формат |0.5| (пауза в секундах) - сначала длинные, чтобы не конфликтовать
        def replace_timed_pause(match):
            time_str = match.group(1)
            try:
                seconds = float(time_str)
                if seconds <= 0.3:
                    return ', '
                elif seconds <= 0.7:
                    return '; '
                else:
                    return '. '
            except ValueError:
                return ', '
        
        text = re.sub(r'\|(\d+\.?\d*)\|', replace_timed_pause, text)
        
        # Обрабатываем простые маркеры: ||| (самый длинный сначала)
        # ||| -> точка (длинная пауза)
        text = re.sub(r'\|\|\|', '. ', text)
        
        # || -> точка с запятой (средняя пауза)
        text = re.sub(r'\|\|', '; ', text)
        
        # | -> запятая (короткая пауза)
        # Используем негативный просмотр вперед и назад, чтобы не захватить || или |||
        text = re.sub(r'(?<!\|)\|(?!\|)', ', ', text)
        
        return text

    @staticmethod
    def process_stress_marks(text: str) -> str:
        """
        Обрабатывает ударения в тексте.
        
        Поддерживаемые форматы:
        - Апостроф перед ударным слогом: у'дарение (espeak-ng формат)
        - Квадратные скобки: у[удар]рение -> у'ударение
        - Фигурные скобки: у{удар}рение -> у'ударение
        
        :param text: Текст с ударениями
        :return: Текст с обработанными ударениями для espeak-ng
        """
        # Обрабатываем формат с квадратными скобками: у[удар]рение
        # Заменяем на: у'ударение
        # Используем [а-яА-ЯёЁ\w] для поддержки русских букв
        text = re.sub(r'([а-яА-ЯёЁ\w]+)\[([а-яА-ЯёЁ\w]+)\]([а-яА-ЯёЁ\w]*)', r"\1'\2\3", text)
        
        # Обрабатываем формат с фигурными скобками: у{удар}рение
        # Заменяем на: у'ударение
        text = re.sub(r'([а-яА-ЯёЁ\w]+)\{([а-яА-ЯёЁ\w]+)\}([а-яА-ЯёЁ\w]*)', r"\1'\2\3", text)
        
        # Апострофы уже в правильном формате для espeak-ng, оставляем как есть
        # Также поддерживаем Unicode символы ударения (combining characters)
        
        return text

    @staticmethod
    def process_control_marks(text: str) -> str:
        """
        Обрабатывает все элементы управления речью: паузы, ударения и другие.
        
        :param text: Текст с маркерами управления
        :return: Обработанный текст для синтеза
        """
        # Сначала обрабатываем паузы (до обработки ударений, чтобы не конфликтовать)
        text = VoiceService.process_pauses(text)
        
        # Затем обрабатываем ударения
        text = VoiceService.process_stress_marks(text)
        
        return text

    def clean_text(self, text: str) -> str:
        """
        Очищает текст от HTML-тегов и лишних пробелов.
        
        :param text: Исходный текст
        :return: Очищенный текст
        """
        # Заменяем <br> на пробелы, удаляем остальные теги
        text_cleaned = re.sub(r'<br\s*/?>', ' ', text, flags=re.IGNORECASE)
        text_cleaned = re.sub(r'<[^>]+>', '', text_cleaned)
        # Убираем лишние пробелы
        text_cleaned = ' '.join(text_cleaned.split())
        return text_cleaned
    
    def _text_to_wav(self, text: str) -> bytes:
        """
        Преобразует текст в WAV аудио.

        :param text: Текст для синтеза (может содержать ударения, паузы и другие элементы управления)
        :return: Байты WAV файла
        """
        if not text.strip():
            raise ValueError("Текст не может быть пустым")
        
        # Обрабатываем все элементы управления (паузы, ударения и т.д.)
        text = self.process_control_marks(text)
        
        # Ограничиваем длину текста (VK имеет ограничения на размер голосовых сообщений)
        max_length = 1000
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        # Создаем WAV файл в памяти
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            self.voice.synthesize_wav(text, wav_file, syn_config=self.syn_config)
        
        wav_buffer.seek(0)
        return wav_buffer.read()

    def _text_to_ogg(self, text: str) -> bytes:
        """
        Преобразует текст в OGG аудио (формат, используемый VK).

        :param text: Текст для синтеза
        :return: Байты OGG файла
        """
        wav_data = self._text_to_wav(text)
        
        if PYDUB_AVAILABLE:
            try:
                # Загружаем WAV в pydub для обработки
                audio = AudioSegment.from_wav(io.BytesIO(wav_data))
                
                # Понижаем тон на 3 полутона для более низкого голоса
                # Отрицательное значение = ниже тон
                audio = audio._spawn(audio.raw_data, overrides={
                    "frame_rate": int(audio.frame_rate * 0.84)  # Понижение на ~3 полутона
                }).set_frame_rate(audio.frame_rate)
                
                # Нормализуем аудио для лучшего качества
                audio = normalize(audio)
                
                # Экспортируем обратно в WAV
                wav_buffer = io.BytesIO()
                audio.export(wav_buffer, format="wav")
                wav_buffer.seek(0)
                return wav_buffer.read()
            except Exception as e:
                # Если обработка не удалась, возвращаем оригинальный WAV
                logger.warning(f"Не удалось обработать аудио через pydub: {e}")
                return wav_data
        
        # Если pydub недоступен, возвращаем WAV (VK также принимает WAV)
        return wav_data
    
    def generate_voice_message(self, text: str, output_path: Optional[str] = None) -> bytes:
        """
        Генерирует голосовое сообщение из текста.
        
        :param text: Текст для озвучки
        :param output_path: Путь для сохранения файла (опционально)
        :return: Байты аудиофайла
        """
        # Очищаем текст
        text_cleaned = self.clean_text(text)
        
        if not text_cleaned:
            raise ValueError("Текст пуст после очистки")
        
        # Генерируем голосовое сообщение
        audio_data = self._text_to_ogg(text_cleaned)
        
        # Сохраняем во временный файл, если указан путь
        if output_path:
            output_file = Path(output_path)
            output_file.write_bytes(audio_data)
            logger.info(f"Голосовое сообщение сохранено в {output_path}")
        
        return audio_data
    
    def save_audio_to_temp_file(self, audio_data: bytes, temp_path: str = "temp_voice.wav") -> Path:
        """
        Сохраняет аудиоданные во временный файл.
        
        :param audio_data: Байты аудиофайла
        :param temp_path: Путь к временному файлу
        :return: Путь к созданному файлу
        """
        temp_file = Path(temp_path)
        temp_file.write_bytes(audio_data)
        return temp_file




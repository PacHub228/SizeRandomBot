"""
Генератор капч в стиле @BestRandom_bot
Создаёт изображения с числами и размытием по краям
"""
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io


class CaptchaGenerator:
    """Генератор числовых капч"""
    
    def __init__(self):
        pass
    
    def generate_captcha(self) -> tuple[Image.Image, str]:
        """
        Сгенерировать капчу с 4 цифрами
        Возвращает (изображение, правильный_ответ)
        """
        # Генерируем 4 случайные цифры
        digits = [str(random.randint(0, 9)) for _ in range(4)]
        answer = ''.join(digits)
        
        width = 280
        height = 80
        
        # Создаем изображение с белым фоном
        image = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)
        
        # Рисуем фоновый шум (легкие серые точки)
        for x in range(width):
            for y in range(height):
                if random.random() < 0.05:
                    gray = random.randint(220, 245)
                    draw.point((x, y), fill=(gray, gray, gray))
        
        # Рисуем линии-помехи
        for _ in range(5):
            color = (
                random.randint(180, 220),
                random.randint(180, 220),
                random.randint(180, 220)
            )
            start = (random.randint(0, width), random.randint(0, height))
            end = (random.randint(0, width), random.randint(0, height))
            draw.line([start, end], fill=color, width=1)
        
        # Выбираем шрифт
        try:
            font = ImageFont.truetype("arial.ttf", 48)
        except:
            try:
                font = ImageFont.truetype("DejaVuSans-Bold.ttf", 48)
            except:
                font = ImageFont.load_default()
        
        # Вычисляем общую ширину текста
        char_widths = []
        for digit in digits:
            bbox = draw.textbbox((0, 0), digit, font=font)
            char_widths.append(bbox[2] - bbox[0])
        
        total_width = sum(char_widths) + 20  # отступы между цифрами
        start_x = (width - total_width) // 2 + 10
        start_y = (height - 48) // 2
        
        # Рисуем каждую цифру
        for i, digit in enumerate(digits):
            digit_x = start_x + sum(char_widths[:i]) + i * 5
            digit_y = start_y + random.randint(-3, 3)
            
            # Случайный поворот для каждой цифры
            angle = random.randint(-10, 10)
            
            # Создаем отдельное изображение для цифры
            char_bbox = draw.textbbox((0, 0), digit, font=font)
            char_w = char_bbox[2] - char_bbox[0] + 10
            char_h = char_bbox[3] - char_bbox[1] + 10
            
            char_image = Image.new('RGBA', (char_w, char_h), (255, 255, 255, 0))
            char_draw = ImageDraw.Draw(char_image)
            
            # Темный цвет для цифры
            text_color = (
                random.randint(20, 60),
                random.randint(20, 60),
                random.randint(20, 60)
            )
            char_draw.text((5, 5), digit, font=font, fill=text_color)
            
            # Поворачиваем
            char_image = char_image.rotate(angle, expand=True, resample=Image.BICUBIC)
            
            # Вставляем на основное изображение
            image.paste(char_image, (digit_x, digit_y), char_image)
        
        # Боковые эффекты
        # Левая область
        for x in range(50):
            gray = 200 + int(55 * (x / 50))
            for y in range(height):
                if random.random() < 0.3:
                    draw.point((x, y), fill=(gray, gray, gray))
        
        # Правая область
        for x in range(width - 50, width):
            offset = x - (width - 50)
            gray = 200 + int(55 * (offset / 50))
            for y in range(height):
                if random.random() < 0.3:
                    draw.point((x, y), fill=(gray, gray, gray))
        
        # Рисуем круги помех (исправлено x2 >= x1)
        for _ in range(3):
            color = (
                random.randint(150, 210),
                random.randint(150, 210),
                random.randint(150, 210)
            )
            x1 = random.randint(0, width - 20)
            y1 = random.randint(0, height - 20)
            x2 = x1 + random.randint(5, 20)
            y2 = y1 + random.randint(5, 20)
            draw.ellipse([x1, y1, x2, y2], fill=color)

        image = image.convert('RGB')
        
        return image, answer
    
    def generate_captcha_bytes(self) -> tuple[bytes, str]:
        """Сгенерировать капчу и вернуть байты"""
        image, answer = self.generate_captcha()
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=85)
        return buffer.getvalue(), answer

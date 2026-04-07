import io
import aiohttp
from PIL import Image, ImageDraw, ImageFont
import random
from core.logger import log

async def fetch_image(url: str) -> bytes:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.read()
    except Exception as e:
        # Oops, something went wrong while getting the image!
        log.error(f"Failed to fetch image from {url}: {e}")
    return None

def hex_to_rgba(hex_color, default=(255, 255, 255, 255)):
    if not isinstance(hex_color, str):
        return default
    hex_color = hex_color.lstrip('#')
    try:
        if len(hex_color) == 6:
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4)) + (255,)
        elif len(hex_color) == 8:
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4, 6))
    except:
        pass
    return default

async def get_welcome_card(avatar_url: str, main_text: str, sub_text: str, bg_urls: list, style_config: dict) -> io.BytesIO:
    """This is where the magic happens! We build a beautiful welcome card for new members!"""
    width = style_config.get("card_width", 800)
    height = style_config.get("card_height", 300)
    avatar_size = style_config.get("avatar_size", 150)
    font_size_main = style_config.get("font_size_main", 36)
    font_size_sub = style_config.get("font_size_sub", 26)
    
    main_color_hex = style_config.get("card_main_color", "#ffffff")
    sub_color_hex = style_config.get("card_sub_color", "#c8c8c8")
    overlay_color_hex = style_config.get("overlay_color", "#000000")
    overlay_opacity = style_config.get("overlay_opacity", 90)
    card_bg_color_hex = style_config.get("card_bg_color", "#191A1C")
    avatar_ring_color_hex = style_config.get("avatar_ring_color", "#ffffff")
    padding_x = style_config.get("card_padding_x", 15)
    padding_y = style_config.get("card_padding_y", 15)
    inner_width = width - (padding_x * 2)
    inner_height = height - (padding_y * 2)
    
    # 1. We start with a blank canvas that is totally see-through!
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    
    def create_rounded_mask(w, h, radius):
        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle((0, 0, w, h), radius, fill=255)
        return mask

    # 2. Now we make the rounded dark box that everything sits inside of.
    outer_card_color = hex_to_rgba(card_bg_color_hex, (25, 26, 28, 255))
    outer_mask = create_rounded_mask(width, height, 20)
    outer_card = Image.new("RGBA", (width, height), outer_card_color)
    outer_card.putalpha(outer_mask)
    canvas.paste(outer_card, (0, 0), outer_card)
    
    bg_bytes = None
    bg_is_color = False
    solid_color_rgba = None
    
    if bg_urls:
        bg_choice = random.choice(bg_urls)
        if bg_choice.startswith("#") or (len(bg_choice) in (6, 8) and not bg_choice.startswith("http")):
            if not bg_choice.startswith("#"):
                bg_choice = "#" + bg_choice
            bg_is_color = True
            solid_color_rgba = hex_to_rgba(bg_choice, (40, 40, 40, 255))
        else:
            bg_bytes = await fetch_image(bg_choice)
        
    # 3. Time to put a cool background image or color inside our card!
    inner_bg = None
    if bg_is_color:
        inner_bg = Image.new("RGBA", (inner_width, inner_height), solid_color_rgba)
        inner_mask = create_rounded_mask(inner_width, inner_height, 15)
        inner_bg.putalpha(inner_mask)
        
    elif bg_bytes:
        try:
            bg_image = Image.open(io.BytesIO(bg_bytes)).convert("RGBA")
            # We resize and crop it so it fits perfectly in our frame.
            aspect_bg = bg_image.width / bg_image.height
            aspect_target = inner_width / inner_height
            if aspect_bg > aspect_target:
                new_width = int(aspect_bg * inner_height)
                bg_image = bg_image.resize((new_width, inner_height), Image.LANCZOS)
                left = (new_width - inner_width) // 2
                inner_bg = bg_image.crop((left, 0, left + inner_width, inner_height))
            else:
                new_height = int(inner_width / aspect_bg)
                bg_image = bg_image.resize((inner_width, new_height), Image.LANCZOS)
                top = (new_height - inner_height) // 2
                inner_bg = bg_image.crop((0, top, inner_width, top + inner_height))
                
            # We add a dark overlay so that the white text is easy to read!
            opacity = max(0, min(255, int(overlay_opacity)))
            overlay_rgba = hex_to_rgba(overlay_color_hex, (0, 0, 0, 255))
            dark_overlay = Image.new("RGBA", inner_bg.size, (overlay_rgba[0], overlay_rgba[1], overlay_rgba[2], opacity))
            inner_bg = Image.alpha_composite(inner_bg, dark_overlay)
            
            inner_mask = create_rounded_mask(inner_width, inner_height, 15)
            inner_bg.putalpha(inner_mask)
        except Exception as e:
            log.error(f"Error opening bg: {e}")
            inner_bg = None
            
    if inner_bg:
        canvas.paste(inner_bg, (padding_x, padding_y), inner_bg)

    # Now let's go grab the person's profile picture!
    avatar_bytes = await fetch_image(avatar_url) if avatar_url else None
    if avatar_bytes:
        try:
            avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
        except:
            avatar = Image.new("RGBA", (150, 150), (100, 100, 100, 255))
    else:
        avatar = Image.new("RGBA", (150, 150), (100, 100, 100, 255))
        
    avatar = avatar.resize((avatar_size, avatar_size), Image.LANCZOS)
    
    # This part makes the profile picture round instead of square!
    mask = Image.new("L", avatar.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
    avatar.putalpha(mask)
    
    # Let's draw a nice white circle around the profile picture.
    ring_size = avatar_size + 8
    ring = Image.new("RGBA", (ring_size, ring_size), (0, 0, 0, 0))
    ring_draw = ImageDraw.Draw(ring)
    ring_color_rgba = hex_to_rgba(avatar_ring_color_hex, (255, 255, 255, 255))
    ring_draw.ellipse((0, 0, ring_size, ring_size), fill=ring_color_rgba)
    
    # Put the profile picture inside our pretty ring!
    ring.paste(avatar, (4, 4), avatar)
    
    # We need some nice fonts to write their name on the card!
    font_main = None
    main_font_paths = [
        'core/fonts/Roboto-Bold.ttf',
        'C:/Windows/Fonts/segoeuib.ttf',
        'C:/Windows/Fonts/arialbd.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
        '/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf'
    ]
    for fp in main_font_paths:
        try:
            font_main = ImageFont.truetype(fp, font_size_main)
            break
        except:
            pass
    if not font_main:
        font_main = ImageFont.load_default()
        
    font_sub = None
    sub_font_paths = [
        'core/fonts/Roboto-Regular.ttf',
        'C:/Windows/Fonts/segoeui.ttf',
        'C:/Windows/Fonts/arial.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
        '/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf'
    ]
    for fp in sub_font_paths:
        try:
            font_sub = ImageFont.truetype(fp, font_size_sub)
            break
        except:
            pass
    if not font_sub:
        font_sub = ImageFont.load_default()

    draw = ImageDraw.Draw(canvas)
    
    # We do some math here to see how big the text is so we can center it!
    try:
        bbox1 = draw.textbbox((0, 0), main_text, font=font_main)
        tw = bbox1[2] - bbox1[0]
        th = bbox1[3] - bbox1[1]
    except Exception:
        tw = draw.textlength(main_text, font=font_main)
        th = font_size_main
        
    try:
        bbox2 = draw.textbbox((0, 0), sub_text, font=font_sub)
        stw = bbox2[2] - bbox2[0]
        sth = bbox2[3] - bbox2[1]
    except Exception:
        stw = draw.textlength(sub_text, font=font_sub)
        sth = font_size_sub
        
    # We do even more math to make sure everything is perfectly centered vertically!
    space1 = style_config.get("text_margin_top", 10)
    space2 = style_config.get("text_spacing", 10)
    total_height = ring_size + space1 + th + space2 + sth
    
    # Finally, we put the profile picture and text onto our main canvas!
    avatar_x = (width - ring_size) // 2
    avatar_y = (height - total_height) // 2
    canvas.paste(ring, (avatar_x, avatar_y), ring)
    main_color_rgba = hex_to_rgba(main_color_hex, (255, 255, 255, 255))
    sub_color_rgba = hex_to_rgba(sub_color_hex, (200, 200, 200, 255))
    
    main_y = avatar_y + ring_size + space1
    draw.text(((width - tw) // 2, main_y), main_text, fill=main_color_rgba, font=font_main)
    
    sub_y = main_y + th + space2
    draw.text(((width - stw) // 2, sub_y), sub_text, fill=sub_color_rgba, font=font_sub)
    
    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

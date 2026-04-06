import asyncio
import json
import os
from core.image_generator import get_welcome_card

async def main():
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
        
    welcome_config = config.get("welcome", {})
    
    avatar_url = "https://cdn.discordapp.com/avatars/317244795800125448/f3c92da1ee50cd662d556ad5e7a9e6af.png?size=256"
    
    # Use random hex colors or image
    bg_urls = welcome_config.get("images", ["0c0d10"])
    
    main_text = "Teszt Elek csatlakozott a szerverhez!"
    sub_text = "Ő a 42. tag"
    
    print("Generating image...")
    buffer = await get_welcome_card(
        avatar_url=avatar_url,
        main_text=main_text,
        sub_text=sub_text,
        bg_urls=bg_urls,
        style_config=welcome_config
    )
    
    output_path = "test_welcome.png"
    with open(output_path, "wb") as f:
        f.write(buffer.read())
        
    print(f"Image saved to {output_path}")
    
    # Auto open in Windows
    os.startfile(output_path)

if __name__ == "__main__":
    asyncio.run(main())

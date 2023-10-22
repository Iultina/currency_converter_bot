import time
import logging
from bots.currency_converter_bot.main import main

if __name__ == '__main__': 
    # while True: 
    #     try: 
    #         main() 
    #         break 
    #     except Exception as e: 
    #         logger.error(f'Ошибка: {e}. Перезапуск через 1 секунду')
    #         time.sleep(1)
    main()
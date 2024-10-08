import asyncio
import requests
import logging
import re
import random
import string
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import pandas as pd

df = pd.DataFrame()

def generate_random_code(n):
    all_characters = string.ascii_lowercase + string.digits
    random_code = ''.join(random.choice(all_characters) for _ in range(n))
    return random_code

async def product(page, href):
    print(f"Processing URL: {href}")
    retry_count = 0
    max_retries = 3
    while retry_count < max_retries:
        try:
            await page.goto(href, timeout=60000)
            await page.wait_for_load_state('load')
            break
        except Exception as e:
            print(f"Error occurred: {e}. Retrying...")
            retry_count += 1
            await asyncio.sleep(5)
    else:
        print(f"Failed to process {href} after 3 retries. Skipping.")
        return

    page_content = await page.content()
    item_modifiedDate = re.findall(r'"modifiedDate":"([\d\-\:T.]+)Z"', page_content) #获取modifiedDate，没有modifiedDate
    if item_modifiedDate:
        modifiedDates = item_modifiedDate
        print(modifiedDates)
    else:
        print("modifiedDate not found")
        modifiedDates = None

    item_name = await page.query_selector('#pdp_product_title')
    name = await item_name.inner_text()  # 使用 inner_text 方法获取文本
    
    item_type = await page.query_selector('#RightRail > div > div:nth-child(1) > div > div.d-lg-ib.mb0-sm.u-full-width.css-3rkuu4.css-1mzzuk6 > div > h2')
    if item_type:
        type_string = await item_type.inner_text()
        male_index = type_string.find("男子")
        female_index = type_string.find("女子")
        if male_index!= -1 and female_index!= -1:
            type = f"男子|女子{type_string[female_index + 2:]}"
        elif male_index!= -1:
            type = type_string[type_string.index("男子"):]
        elif female_index!= -1:
            type = type_string[type_string.index("女子"):]
        else:
            type = "无"

    item_number = await page.query_selector('#RightRail > div > span > div > div > ul > li.description-preview__style-color.ncss-li')
    number = await item_number.inner_text()
    number = number.strip('款式： ')

    system_number = generate_random_code(8)

    item_price = await page.query_selector('#RightRail > div > div:nth-child(1) > div > div.d-lg-ib.mb0-sm.u-full-width.css-3rkuu4.css-1mzzuk6 > div > div > div > div > div')
    price = await item_price.inner_text()
    price = price.strip('¥')
    price = price.replace(',', '')

    item_size = await page.query_selector('#buyTools > div.prl6-sm.prl0-lg > fieldset > div')
    if item_size:  # 先检查是否获取到了元素
        labels = await item_size.query_selector_all('label')
        sizes = [await label.text_content() for label in labels]
        sizes = "|".join(sizes)
    else:
        sizes = "商品售罄，无尺寸信息"  # 或者您想要设置的其他默认值

    item_color = await page.query_selector('#RightRail > div > span > div > div > ul > li.description-preview__color-description.ncss-li')
    color = await item_color.inner_text()
    color = color.strip('显示颜色： ')
    
    item_introduction = await page.query_selector('#RightRail > div > span > div > div > p')
    introduction = await item_introduction.inner_text()
    
    item_picture = await page.query_selector('#PDP > div.app-root > div > div:nth-child(4) > div.css-1e4ja6z.css-1wpyz1n > div.css-1rayx7p')
    pictures = await item_picture.query_selector_all('picture')
    image_urls = []
    for picture in pictures:
        img = await picture.query_selector('img')
        image_url = await img.get_attribute('src')   
        random_filename = generate_random_code(8)
        file_path = f"images/{system_number}/{random_filename}.jpg"
        image_urls.append(file_path)
    image_urls = "|".join(image_urls)
    #print("|".join(image_urls))
    data = {
        '名称': [name],
        '类型': [type],
        '编号': [number],
        '系统编号': [system_number],
        '价格': [price],
        '尺寸': [sizes],
        '颜色': [color],
        '介绍': [introduction],
        '图片链接': [image_urls],
        '网站被修改时间戳':[modifiedDates]
    }
    global df  # 声明使用全局的 df
    df = pd.concat([df, pd.DataFrame(data)], ignore_index=True)
    await asyncio.sleep(1)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        while True:
            page_count = 0 
            if page_count == 0: 
                page = await context.new_page()
                page_count = 1
            else:
                print("已有页面，不再创建新页面")
            url = 'https://www.nike.com.cn/w/3rauvz5e1x6z6bvfkz6ymx6znik1zy7ok'
            await page.goto(url)
            await page.wait_for_load_state('load')
            print("页面下滑中......")
            i = 0
            while i < 2:
                await page.evaluate("() => window.scrollTo(0,document.body.scrollHeight)")
                await page.wait_for_load_state('load')
                await asyncio.sleep(2)
                print(i)
                i = i + 1
            #获取商品的链接    
            elements = await page.query_selector_all('#skip-to-products > *:nth-child(n + 2) figure > a.product-card__link-overlay')
            hrefs = []
            for element in elements:
                href = await element.get_attribute('href')
                hrefs.append(href)
            #print(hrefs)
            print(len(hrefs))
            for href in hrefs:
                await product(page, href)
            df.to_csv('C:/Users/12391/Desktop/nike/商品信息.csv', index=False)  # 在循环结束后统一保存到 Excel
            print("程序运行完毕")
            await asyncio.sleep(5)
            await browser.close()

asyncio.run(main())
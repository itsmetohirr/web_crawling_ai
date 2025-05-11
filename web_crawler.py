import os
import asyncio
import logging

from dotenv import load_dotenv

from firecrawl import FirecrawlApp

from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

import gspread
from google.oauth2.service_account import Credentials

from pyairtable import Api


load_dotenv(override=True)
logging.basicConfig(level=logging.INFO)


def crawl(website):
    logging.info('Authenticating Firecrawl...')
    firecrawl = FirecrawlApp(api_key=os.getenv('FIRECRAWL_API'))
    logging.info('Authenticated Firecrawl.')
    logging.info('Started scraping the website...')
    scrape_result = firecrawl.scrape_url(website, formats=['markdown'])
    logging.info('Finished scraping.')
    markdown = scrape_result.markdown.strip()

    return markdown


def ai_modify(markdown):
    logging.info('Authenticating OpenAI...')
    llm = ChatOpenAI(openai_api_key=os.getenv('OPENAI_API'), temperature=0)
    logging.info('Authenticated OpenAI.')

    prompt = PromptTemplate(
        input_variables=["web_data"],
        template="Given the website data \"{web_data}\" Make sense of the data and provide information about the website.")

    chain = prompt | llm
    logging.info('Waiting for OpenAI\'s response...')
    result = chain.invoke({"web_data": markdown})
    logging.info('Got the result from OpenAI')
    return result.content


async def update_sheets(website, result):
    SERVICE_ACCOUNT_FILE = 'creds.json'
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    SPREADSHEET_ID = '1VarAr4qbBgM-0ixXa_-GrlDMy3y6bTz1EDipnAqps1E'

    logging.info('Connecting to Google sheets...')
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    workbook = client.open_by_key(SPREADSHEET_ID)
    sheet = workbook.worksheet('Sheet1')
    sheet.append_row([website, result])
    logging.info('Result has been saved to Google Sheets.')


async def update_airtable(website, result):
    api = Api(os.getenv('AIRTABLE_API_KEY'))
    table = api.table('app91Xn5ozfJumoDi', 'tblQOUjnjIU5MWXPM')

    data = {
        'Website': website,
        'Info': result
    }

    table.create(data)
    logging.info('Result has been saved to Airtables.')


async def main():
    website = input('Enter a website url: ')
    markdown = crawl(website)
    result = ai_modify(markdown)

    await asyncio.gather(
        update_sheets(website, result),
        update_airtable(website, result)
    )


if __name__ == '__main__':
    asyncio.run(main())

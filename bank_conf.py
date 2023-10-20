#!/usr/bin/env python3

from docxtpl import DocxTemplate
import pandas as pd
import jinja2
from typing import Generator
from datetime import datetime
# import re


class Context:
    def __init__(self, attrValue: list) -> None:
        self.get_account(attrValue)
        self.get_manager(default=True)
        self.get_date()

    def get_account(self, attrValue):
        attrName = ['demandAcc', 'fixedAcc', 'debtAcc', 'bank', 'ref', 'payAccount', 'tips', 'format', 'brkPage']
        for k, v in zip(attrName, attrValue):
            setattr(self, k, v)

    def get_date(self) -> None:
        self.today = datetime.today().strftime('%Y年%m月%d日')
        key = ('year1', 'month1', 'day1', 'year2', 'month2', 'day2')
        date = '-'.join(self.dateRange).split('-')
        for key, value in zip(key, date):
            setattr(self, key, value)

    def get_manager(self, default):
        if default:
            self.dateRange = ('2022-1-1', '2022-12-31')
            self.company = 'xxxx（xx）有限公司'
            self.manager = {
                'name': 'xxx',
                'email': 'xxxxxxxxx@xxx',
                'tel': 'xxxxxxxx'
            }


def prase(df: pd.DataFrame):
    new_cols = 'bank account currency rate nature amount pool dateStart dateEnd restriction ref mortgage format'.split(' ')
    # cols = [re.sub(".*资金归集.*", '资金归集', col) for col in df.columns]
    # cols = [re.sub('.*担保.*', '担保', col) for col in df.columns]  # type:ignore
    # mapping = dict(zip(df.columns, new_cols))
    # df = df.rename(columns=mapping)
    df.columns = new_cols
    if set(df.columns) < set(new_cols):
        raise Exception
    if df['amount'].dtype == 'object':
        df['amount'] = df['amount'].apply(lambda x: x.strip()).replace('-', '0.00')
        df['amount'] = df['amount'].apply(lambda x: x.strip()).replace(',', '')
        df['amount'] = df['amount'].astype(float)
    if df['rate'].dtype == 'float':
        # df.style.format({'rate': lambda x: '{:.2%}'.format(x)})
        df['rate'] = df.loc[df['rate'].notna(), 'rate'].apply(lambda x: '{:.2%}'.format(x))
    df.loc[df['rate'].isna(), 'rate'] = '活期'
    if not df[df['dateStart'].notna()].empty:
        df['dateStart'] = df['dateStart'].dt.strftime('%Y-%m-%d')
        df['dateEnd'] = df['dateEnd'].dt.strftime('%Y-%m-%d')
    df.loc[df['restriction'].isna(), 'restriction'] = '否'
    df.loc[df['pool'].isna(), 'pool'] = '否'
    df.loc[df['mortgage'].isna(), 'mortgage'] = '无'
    df['format'] = df['format'].astype(str)
    df['ref'] = df['ref'].str.replace(r'<|>', '', regex=True)
    return df


def judge_balance(df: pd.DataFrame):
    balance = df[df['amount'] > 200]
    baseAccount = balance[balance['nature'].str.contains('基本', na=False)]
    normalAcc = balance[balance['nature'].str.contains('一般', na=False)]
    if balance.empty:
        payAccount = df.iloc[0]['account']
        tips = '-余额不足'
        caution = "余额不足！"
    elif not baseAccount.empty:
        payAccount = baseAccount.iloc[0]['account']
        tips = ''
        caution = None
    elif not normalAcc.empty:
        payAccount = normalAcc.iloc[0]['account']
        tips = ''
        caution = None
    else:
        payAccount = df.iloc[0]['account']
        tips = '-没有一般户'
        caution = "没有一般户!"
    return payAccount, tips, caution


def const_context(df: pd.DataFrame) -> Generator:
    df = prase(df)
    groups = df.groupby(['bank', 'ref'])
    for index, df in groups:
        # convert df to a list of dicts like [{col1: value1}, {col2, value2}]
        bank = index[0]
        ref = index[1]
        DocxFormat = 2 if df['format'].str.contains('二').any() else 1
        payAccount, tips, caution = judge_balance(df)
        if caution:
            print(' '.join([ref, bank, caution]))
        # format float to 2 decimal places and to use a comma separator for the thousands
        df['amount'] = df['amount'].map('{:,.2f}'.format)
        debtAcc = df[df['nature'].str.contains('贷款')].to_dict('records')
        df = df[~df['nature'].str.contains('贷款')]
        demandAcc = df[df['dateStart'].isna()].to_dict('records')
        fixedAcc = df[df['dateStart'].notna()].to_dict('records')
        counter = len(demandAcc) + len(fixedAcc)
        brkPage = {'account': (counter == 2)}
        yield Context([demandAcc, fixedAcc, debtAcc, bank, ref, payAccount, tips, DocxFormat, brkPage])


def fill_template(context: dict, template: str) -> tuple[str, DocxTemplate]:
    tpl = DocxTemplate(template)
    jinja_env = jinja2.Environment(autoescape=True)
    tpl.render(context, jinja_env)
    filename = f"{context['ref']}-{context['bank']}{context['tips']}.docx"
    return filename, tpl


if __name__ == '__main__':
    # os.chdir('/home/guest/下载/test/')
    # df = pd.read_clipboard()
    df = pd.read_excel('template.xlsx')
    contexts = const_context(df)
    for context in contexts:
        template = 'bank_temp.docx'
        filename, tpl = fill_template(vars(context), template)
        tpl.save('build/'+filename)

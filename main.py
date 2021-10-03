from decimal import Decimal
import http
import os
import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Dict, Any, Tuple, List, Optional

import aiohttp
from aiohttp import hdrs
from dotenv import load_dotenv
from pydantic import BaseModel, NoneStr

load_dotenv()

TOKEN: str = os.getenv('token')
HOST: str = os.getenv('host')


class Transaction(BaseModel):
    destination_id: int
    source_id: int
    type: str
    date: str
    amount: str
    description: str
    category_name: NoneStr = None
    tags: List[NoneStr] = None


class Transactions(BaseModel):
    transactions: List[Transaction]


async def _requests(method: str, url: str, headers: Dict[str, str], data: Any = None):
    kwargs = {}
    if data:
        kwargs['data'] = data

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.request(method=method, url=url, **kwargs) as resp:
            status = resp.status
            try:
                resp_json = await resp.json()
            except Exception as ex:
                print(f'_requests.Exception ex={ex}')
                raise
            if status != http.HTTPStatus.OK:
                print(f'_requests.Exception status={status}')
                raise


async def create_transaction(data: Transactions):
    await _requests(
        hdrs.METH_POST,
        f'{HOST}api/v1/transactions',
        headers={
            'Authorization': f'Bearer {TOKEN}',
            'Content-Type': 'application/json',
            'accept': 'application/vnd.api+json',
        },
        data=data.json()
    )


def find(d: Dict[Any, Any], keys: Tuple[Any, ...]) -> Any:
    value = d
    try:
        for k in keys:
            value = value[k]
    except (KeyError,):
        return None
    return value


class SubGroup(Enum):
    A1 = auto()  #
    A2 = auto()  # Возврат

    B1 = auto()  # Снятия наличных

    # 'Банковский перевод. УФК'
    C1 = auto()  # Пополнения
    # 'Перевод с карты'
    C2 = auto()  # Пополнения
    # 'Входящий перевод'
    C4 = auto()  # Пополнения
    # 'Перевод между счетами' - Пополнение
    C5 = auto()  # Пополнения

    # 'Комиссия за операцию перевода'
    D1 = auto()  # Комиссии
    # 'Плата за обслуживание'
    D2 = auto()  # Услуги банка

    E4 = auto()  # Cashback
    E5 = auto()  # Бонусы

    # 'Перевод между счетами' - Исходяший
    F1 = auto()  # Переводы


async def main():
    cash = 10
    credit = 8
    main_cart = 7
    iis = 17

    cart = main_cart

    # file = '2021-10-03T190457.200.json'
    file = '2021-10-03T221608.200.json'
    with open(f'tmp/{file}', mode='rb') as f:
        data = json.load(f)

    for p in data['payload']:
        pid = p['id']
        status = p['status']
        create_at = datetime.fromtimestamp(p['operationTime']['milliseconds'] / 1000)
        name = p['description']
        payment_type = find(p, ('payment', 'paymentType',))
        category = p['category']['name']
        category = category if category != 'ДРУГИЕ ОПЕРАЦИИ' else None
        subgroup = find(p, ('subgroup', 'id'))

        value = p['accountAmount']['value']
        rounding = find(p, ('rounding', 'accountAmount', 'value'))
        if rounding:
            value = Decimal(value) + Decimal(rounding)
            value = value.quantize(Decimal('0.00'))

        if status != 'OK':
            continue

        if subgroup in (i.name for i in (SubGroup.C1, SubGroup.C2, SubGroup.C4)):
            t = Transaction(
                source_id=cash,
                destination_id=cart,
                type='deposit',
                date=create_at.isoformat(),
                amount=str(value),
                description=name,
                category_name=category,
                tags=[category],
            )
            t = None
        elif subgroup == SubGroup.F1.name and name == 'Пополнение брокерского счета':
            t = Transaction(
                source_id=cart,
                destination_id=iis,
                type='transfer',
                date=create_at.isoformat(),
                amount=str(value),
                description=name,
                category_name=category,
                tags=[category],
            )
        else:
            t = Transaction(
                source_id=cart,
                destination_id=cash,
                type='withdrawal',
                date=create_at.isoformat(),
                amount=str(value),
                description=name,
                category_name=category,
                tags=[category],
            )
            t = None

        if pid == '':
            break

        if t:
            print(f'new item description={name} sum={value} id={pid}')
            await create_transaction(Transactions(transactions=[t]))
            print(f'done id={pid}')


if __name__ == '__main__':
    asyncio.run(main())

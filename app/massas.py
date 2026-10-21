"""Massa inicial da simulação OpenRocket correspondente ao CSV ativo."""

import hashlib
import math
import re
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path


RAIZ_MODELOS = Path(__file__).resolve().parent.parent / 'Foguete Modular - Banco' / 'gerados'
CODIGO = re.compile(r'C[1-3]-A[1-3]-F[3-5]-S[1-4]')


@lru_cache(maxsize=128)
def massa_inicial_kg(codigo, hash_csv):
    """Lê a massa em t=0 do ORK apenas se o CSV dele for a simulação ativa."""
    if not CODIGO.fullmatch(codigo) or not hash_csv:
        return None
    relativo = Path(codigo[:2]) / codigo[3:5] / codigo[6:8] / codigo
    csv = RAIZ_MODELOS / 'csv' / relativo.with_suffix('.csv')
    ork = RAIZ_MODELOS / 'ork' / relativo.with_suffix('.ork')
    try:
        if hashlib.sha256(csv.read_bytes()).hexdigest() != hash_csv:
            return None
        ramo = ET.parse(ork).find('.//databranch')
        colunas = ramo.get('types').split(',')
        indice = next(i for i, coluna in enumerate(colunas) if coluna.endswith('TYPE_MASS]'))
        massa = float(ramo.findtext('datapoint').split(',')[indice])
    except (OSError, ET.ParseError, AttributeError, StopIteration, ValueError, IndexError):
        return None
    return massa if math.isfinite(massa) and massa > 0 else None

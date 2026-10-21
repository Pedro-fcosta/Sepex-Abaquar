"""Regras operacionais aplicadas às simulações e ao placar."""

MARGEM_MINIMA_CALIBRES = 0.10


def missao_abortada(margem_calibres):
    return margem_calibres is not None and margem_calibres < MARGEM_MINIMA_CALIBRES

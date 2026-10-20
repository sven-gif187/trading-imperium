# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Messmodul zum Audit F1/F2/F3 vom 30.07.2026.
# Nicht archivieren - Beleg fuer die Kostenhuerden- und Feature-Messung.
"""
messung_f_stat.py - gemeinsame Statistik fuer F1/F2/F3.

KEIN LAUF. Modul, analog zu harness_ext.py fuer E1/E2/E5.
Ausschliesslich Standardbibliothek (kein numpy/scipy), damit die Ergebnisse
ohne Fremdpakete reproduzierbar bleiben - gleiche Konvention wie E1/E2/E5.

Enthaelt:
  rang()             - Durchschnittsraenge mit Bindungsbehandlung
  spearman()         - Rangkorrelation (Pearson auf Raengen)
  t_p_zweiseitig()   - p-Wert der t-Verteilung ueber unvollstaendige Betafn.
  bh_fdr()           - Benjamini-Hochberg, gibt q-Werte zurueck
  median/quantil     - ohne numpy

WARUM n_eff
-----------
Forward-Renditen ueber h Balken ueberlappen sich: benachbarte Beobachtungen
teilen h-1 Balken und sind massiv autokorreliert. Ein t-Test auf der rohen
Zahl der Beobachtungen unterschaetzt den Standardfehler um rund sqrt(h).
Zusaetzlich sind die 11 Coins im gepoolten Test nicht unabhaengig - E5
misst eine mittlere Paarkorrelation von 0,72-0,75 und N_eff = 1,23-1,42
(BEFUNDE.md, Befund 16). Beide Effekte werden ueber eine reduzierte
effektive Stichprobe abgebildet:

    n_eff = n / h            (Ueberlappung, je Coin)
    n_eff = n / (h * k)      (gepoolt, k = coins / N_eff)

Das ist eine grobe, aber in die SICHERE Richtung grobe Korrektur.
Der rohe p-Wert wird trotzdem ausgegeben, wie beauftragt.
"""
import math


# ===========================================================================
# Lagemasse
# ===========================================================================
def median(xs):
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return 0.0
    m = n // 2
    return s[m] if n % 2 else (s[m - 1] + s[m]) / 2.0


def quantil(xs, q):
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return 0.0
    pos = (n - 1) * q
    lo = int(math.floor(pos))
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    return s[lo] * (1 - frac) + s[hi] * frac


def mittel(xs):
    return sum(xs) / len(xs) if xs else 0.0


def stdabw(xs):
    n = len(xs)
    if n < 2:
        return 0.0
    m = mittel(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))


# ===========================================================================
# Rangkorrelation
# ===========================================================================
def rang(xs):
    """Durchschnittsraenge; Bindungen bekommen den mittleren Rang."""
    idx = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(idx):
        j = i
        while j + 1 < len(idx) and xs[idx[j + 1]] == xs[idx[i]]:
            j += 1
        mittlerer = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            r[idx[k]] = mittlerer
        i = j + 1
    return r


def pearson(a, b):
    n = len(a)
    if n < 3:
        return 0.0
    ma, mb = mittel(a), mittel(b)
    sa = sb = sab = 0.0
    for x, y in zip(a, b):
        dx, dy = x - ma, y - mb
        sa += dx * dx
        sb += dy * dy
        sab += dx * dy
    if sa <= 0 or sb <= 0:
        return 0.0
    return sab / math.sqrt(sa * sb)


def spearman(x, y):
    """Spearman-Rangkorrelation. Gibt (rho, n) zurueck."""
    if len(x) != len(y) or len(x) < 3:
        return 0.0, len(x)
    return pearson(rang(x), rang(y)), len(x)


# ===========================================================================
# p-Werte
# ===========================================================================
def _betacf(a, b, x, itmax=300, eps=3e-12):
    """Kettenbruch fuer die unvollstaendige Betafunktion (Numerical Recipes)."""
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d
    for m in range(1, itmax + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < eps:
            break
    return h


def betainc(a, b, x):
    """Regularisierte unvollstaendige Betafunktion I_x(a,b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
             + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return math.exp(lbeta) * _betacf(a, b, x) / a
    return 1.0 - math.exp(lbeta) * _betacf(b, a, 1.0 - x) / b


def t_p_zweiseitig(t, df):
    """Zweiseitiger p-Wert der Student-t-Verteilung."""
    if df <= 0:
        return 1.0
    t = abs(t)
    if t == 0.0:
        return 1.0
    return betainc(df / 2.0, 0.5, df / (df + t * t))


def rho_p(rho, n_eff):
    """p-Wert einer (Rang-)Korrelation bei effektiver Stichprobe n_eff."""
    if n_eff < 4 or abs(rho) >= 1.0:
        return 1.0
    t = rho * math.sqrt((n_eff - 2.0) / (1.0 - rho * rho))
    return t_p_zweiseitig(t, n_eff - 2.0)


# ===========================================================================
# Multiples Testen
# ===========================================================================
def bh_fdr(ps):
    """Benjamini-Hochberg. Gibt q-Werte in der Reihenfolge der Eingabe."""
    m = len(ps)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: ps[i])
    q = [1.0] * m
    vorher = 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        wert = min(vorher, ps[i] * m / rank)
        q[i] = min(1.0, wert)
        vorher = q[i]
    return q


# ===========================================================================
# IC -> Trefferquote (fuer F2e)
# ===========================================================================
def ic_zu_trefferquote(rho_s):
    """Erwartete Trefferquote des Vorzeichens bei bivariat-normaler Naeherung.

    Spearman -> Pearson: rho_p = 2*sin(pi*rho_s/6)
    Vorzeichen-Trefferquote: 0.5 + arcsin(rho_p)/pi

    ACHTUNG: gilt fuer das Vorzeichen einer Rendite ueber FESTEN Horizont,
    NICHT fuer das First-Touch-Barrierenrennen aus E2. Naeherung, keine
    Messung.
    """
    rp = 2.0 * math.sin(math.pi * rho_s / 6.0)
    rp = max(-0.999999, min(0.999999, rp))
    return 0.5 + math.asin(rp) / math.pi


def trefferquote_zu_ic(p):
    """Umkehrung: welcher Spearman-IC gehoert zu Trefferquote p?"""
    rp = math.sin((p - 0.5) * math.pi)
    rp = max(-0.999999, min(0.999999, rp))
    return 6.0 / math.pi * math.asin(rp / 2.0)

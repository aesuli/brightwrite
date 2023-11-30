import random
import re
from collections import Counter, defaultdict

from tqdm.auto import tqdm

# pattern che individua nel testo le parole e la punteggiatura
cerca_parole = re.compile(r"[0-9]+|[\w]+|[+-,.;:%']", flags=re.UNICODE)


def carica_esempi(filename):
    """
    Legge un file di testo con una frase per riga e suddivide ogni riga nella
    sequenza di parole e punteggiatura
    :param filename: file di testo con una frase per riga
    :return: lista di liste di parole e punteggiatura
    """
    esempi = list()
    with open(filename, mode='rt', encoding='utf-8') as infile:
        linee = infile.readlines()
    for linea in tqdm(linee):
        esempi.append([word if not word.isnumeric() else 'NUM' for word in cerca_parole.findall(linea)])
    return esempi


def stampa_esempi(esempi, num):
    """
    Stampa i primi num esempi
    :param esempi: lista di frasi rappresentate come liste di parole e punteggiatura
    :param num: numero di esempi da stampare
    """
    for i in range(num):
        print(f'{i + 1}\t{" ".join(esempi[i])[:70]}...')


def costruisci_vocabolario(esempi):
    """
    Calcola il vocabolario dagli esempi.
    :param esempi: lista di frasi rappresentate come liste di parole e punteggiatura
    :return: la lista in ordine alfabetico delle parole che compaiono negli esempi
    """
    vocabolario = set()
    # inserisco nel set tutte le parole che compaiono negli esempi
    for esempio in tqdm(esempi):
        vocabolario.update(esempio)
    print(f'Il vocabolario contiene {len(vocabolario)} elementi')
    return sorted(vocabolario)


def conta_frequenze(esempi):
    """
    Calcola il vocabolario e le frequenze dagli esempi.
    :param esempi: lista di frasi rappresentate come liste di parole e punteggiatura
    :return: una lista con due elementi:
     * la lista in ordine di frequenza delle parole che compaiono negli esempi
     * la lista delle frequenze delle rispettive parole
    """
    contatore = Counter()
    # conto la frequenza delle parole negli esempi
    for esempio in esempi:
        contatore.update(esempio)

    # restituisco due liste: il vocabolario e le frequenze
    return list(zip(*contatore.most_common()))


def conta_frequenze_nei_contesti(esempi, contesto_massimo=3, frequenza_minima=2,
                                 frequenza_minima_contesto=3):
    """
    Calcola il vocabolario e le frequenze, condizionati ai contesti, dagli esempi.
    :param esempi: lista di frasi rappresentate come liste di parole e punteggiatura
    :param contesto_massimo: la lunghezza massima, in numero di parole, dei contesti da utilizzare.
    Vengono calcolati tutti i contesti da 0 a contesto_massimo.
    :param frequenza_minima: le parole che compaiono negli esempi meno di frequenza_minima sono cancellate
    dal modello.
    :param frequenza_minima_contesto: i contesti che compaiono negli esempi meno di frequenza_minima_contesto
    sono cancellati dal modello.
    :return: una lista di dizionari, uno per ogni dimensione del contesto.
    Ogni dizionario ha come chiave i contesti osservati negli esempi, e come valori le frequenze delle parole
    osservate negli esempi per quel contesto.
    """
    modello = list()
    for _ in range(contesto_massimo + 1):
        modello.append(defaultdict(Counter))

    # memorizzo tutte le coppie contesto->prossima parola, per varie lunghezze del contesto
    for esempio in tqdm(esempi):
        esempio = [''] + esempio
        for i in range(len(esempio)):
            for c in range(min(i, contesto_massimo) + 1):
                contesto = tuple(esempio[i - c:i])
                modello[c][contesto].update([esempio[i]])

    # rimuovo le parole con frequenza troppo bassa
    tokens_to_delete = set()
    for key, value in modello[0][()].items():
        if value < frequenza_minima:
            tokens_to_delete.add(key)

    for c in range(contesto_massimo + 1):
        keys_to_delete = list()
        for key in modello[c].keys():
            if tokens_to_delete.intersection(key):
                keys_to_delete.append(key)
        keys_to_delete = set(keys_to_delete)
        # rimuovo i contesti che contengono parole rimosse
        modello[c] = {key: {keyc: valuec for keyc, valuec in value.most_common() if keyc not in tokens_to_delete} for
                      key, value in modello[c].items() if key not in keys_to_delete}
        # rimuovo i contesti con frequenza troppo bassa
        modello[c] = {key: value for key, value in modello[c].items() if
                      sum(value.values()) >= frequenza_minima_contesto}
        modello[c] = {key: list(zip(*value.items())) for key, value in modello[c].items()}

    size = 0
    contesti = 0
    for modello_c in modello:
        for contesto, (vocab, freq) in modello_c.items():
            contesti += 1
            size += len(vocab)
    print(f'Numero contesti: {contesti}')
    print(f'Numero totale di parametri: {size}')
    return modello


def mostra_frequenze_per_contesto(modello, contesto, show=10):
    """
    Dato un contesto, stampa la sua distribuzione di frequenze
    :param modello: modello prodotto da conta_frequenze_nei_contesti
    :param contesto: testo che definisce il contesto, per esempio: 'con un'
    :param show: Numero massimo di parole da stampare
    """
    contesto = tuple(cerca_parole.findall(contesto))
    try:
        parole, frequenze = modello[len(contesto)][contesto]
        for i, (parola, frequenza) in enumerate(zip(parole, frequenze)):
            if i >= show:
                print(f'  ... (+{len(parole) - i})')
                break
            print(f'{frequenza:5} {parola:30}', end=' ')
    except:
        print('Contesto sconosciuto')


def genera_testo(modello, contesto=None, lunghezza_min=7, lunghezza_max=20, interrompi_al_punto=True, dettagli=False):
    """
    Genera il testo usando il modello di frequenze con contesto
    :param modello: modello prodotto da conta_frequenze_nei_contesti
    :param contesto: testo che definisce il contesto iniziale, per esempio: 'con un'
    Se non viene fornito si inizia con il contesto vuoto di inizio frase.
    :param lunghezza_min: numero minimo di parole da generare
    :param lunghezza_max: numero massimo di parole da generare.
    :param interrompi_al_punto: la generazione si interrompe prima di lunghezza_max se viene generato un punto '.'
    :param dettagli: stampa alcuni dettagli sul processo di generazione
    :return: testo generato incluso il contesto
    """
    if contesto is None:
        sequenza = ['']
    else:
        sequenza = list(cerca_parole.findall(contesto))
    for i in range(lunghezza_max):
        # Si cerca di utilizzare il contesto più lungo.
        # Se il contesto di c elementi non è stato osservato negli esempi si prova con c-1.
        # Al peggio, per c=0, si sceglie una parola a caso nel vocabolario.
        for c in range(len(modello) - 1, -1, -1):
            try:
                modello_c = modello[c][tuple(sequenza[-c:])]
                parola = random.choices(modello_c[0], k=1, weights=modello_c[1])[0]
                if dettagli:
                    print(
                        f'Contesto: "{" ".join(sequenza[-(len(modello) - 1):])}"\t{sum(modello_c[1])} opzioni\t-> "{parola}"')
                sequenza.append(parola)
                break
            except KeyError:
                pass
        if interrompi_al_punto and sequenza[-1] == '.' and i > lunghezza_min:
            break
    if dettagli:
        print()
    return ' '.join(sequenza)

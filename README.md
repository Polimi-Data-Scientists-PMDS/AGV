# AGV
PMDS x DevNut Autonomous Guided Vehicle project

## TODOS
Check [TODO.md](./TODO.md) for the list of tasks to be done.

## Installazione ambiente di sviluppo
### Come installare le dependencies:
- Installare il virtual enviorment 
```  python3.14 -m venv .venv ```

- Attivare il venv (unico dei tre comandi da fare sempre)
```source .venv/bin/activate```

- Installare i requirements (*requirements.txt è stato aggiornato il 14/03/2026, se ci sono problemi con le dipendenze, controllare che sia aggiornato*)
```pip install -r requirements.txt```

### Come usare il venv in webots:
1. Andare in `.venv > bin > python3.14` e fare tasto destro per copiare il percorso assoluto.
2. Su webots andare in: `Webots > preferences > Python commands` e incollare il nuovo percorso nel box apposito.

### Regole:
- Non salvare da webots il mondo (cmd + shift + S / ctrl + shift + S) altrimenti i commenti del file .wbt vengono persi, nel caso non pushare il codice


## Installazione database su docker

Questa guida ti mostrerà come installare Docker, avviare un container MySQL e creare la struttura del database per salvare i log del tuo simulatore robotico.

### Passo 1: Installare Docker Desktop

1. Vai sul sito ufficiale [docker.com](https://www.docker.com/products/docker-desktop) e scarica **Docker Desktop** per il tuo sistema operativo (Mac, Windows o Linux).
2. Installa l'applicazione seguendo la procedura standard del tuo sistema.
3. Apri Docker Desktop e **attendi che si avvii completamente**.

### Passo 2: Avviare il Container MySQL

Apri il tuo terminale (o Prompt dei comandi) ed esegui questo comando per scaricare e avviare MySQL in background:

```bash
docker run --name agv-logger -e MYSQL_ROOT_PASSWORD=agv_pass -p 3306:3306 -d mysql:latest
```
- **`--name agv-logger`**: Assegna un nome al container per facilitarne la gestione.
- **`-e MYSQL_ROOT_PASSWORD=agv_pass`**: Imposta la password per l'utente root di MySQL (puoi cambiarla se vuoi, ma ricordati!).
- **`-d`**: Avvia il container in modalità "detached" (in background).
- **`-p 3306:3306`**: Espone la porta standard di MySQL per permettere al tuo script Python di comunicare con il database (la porta di sinistra può essere cambiata, per comodità utilizziamo la stessa).
- **`mysql:latest`**: Specifica l'immagine di MySQL da utilizzare: [mysql](https://hub.docker.com/_/mysql).

### Passo 3: Accedere alla Console di MySQL

Ora dobbiamo "entrare" nel container per creare il database. Esegui:

```bash
docker exec -it agv-logger mysql -u root -p
```

*Ti verrà richiesta la password in quanto stiamo entrando come utente root. Digita `agv_pass` e premi Invio (non vedrai i caratteri mentre digiti).*

### Passo 4: Creare il Database e la Tabella

Una volta dentro la console di MySQL (il prompt mostrerà `mysql>`), copia e incolla i seguenti comandi uno alla volta:

**1. Crea e seleziona il database:**

```sql
CREATE DATABASE agv_data;
USE agv_data;
```

**2. Crea le tabelle per il log:**

Copiare ed incollare le diferse query per creare le tabelle che si trovano all'interno di [Database_Structure.sql](Database_Structure.sql) (assicurati di eseguire ogni query separatamente, non tutto in una volta).

Se tutto è andato a buon fine, vedrai il messaggio `Query OK`. Puoi uscire digitando `EXIT;`.

> ricordarsi di installare il nuovo pacchetto di python chiamato `mysql-connector-python`.
---

### Gestione del Container: Uscire, Fermare e Riavviare

#### 1. Uscire dalla console MySQL (`exit`)

Se ti trovi all'interno della riga di comando di MySQL (dove vedi il prompt `mysql>`), devi prima tornare al terminale normale del tuo sistema. Digita semplicemente:

```sql
exit;
```

*(Vedrai il messaggio "Bye" e il terminale tornerà al prompt standard del tuo Mac).*

#### 2. Fermare il container (`docker stop`)

Anche se sei uscito da MySQL, il database sta ancora girando in background. Per "spegnerlo" e liberare le risorse del computer, usa il comando `stop` seguito dal nome che hai dato al tuo container:

```bash
docker stop agv-logger
```

#### 3. Far ripartire il container (`docker start`)

Quando sei pronto a riprendere la tua simulazione su Webots, **non devi eseguire di nuovo il comando `docker run`** (ti darebbe errore dicendo che il nome esiste già). Ti basta "riaccendere" il container esistente:

```bash
docker start agv-logger
```

Una volta avviato bisognerà aspettare rientrare nella console di MySQL (con `docker exec -it agv-logger mysql -u root -p`) e inserendo la password. Dunque selezionare il database (`USE agv_data;`) prima di poter eseguire query o inserire dati.
#  Wolpertingers by MaxMaz 2022 v beta 0.1

#  Dichiara i personaggi usati in questo gioco. L'argomento 'color' colora il nome del personaggio.

define name = "Leopoldo"
define player = Character("[name]", color="#FFD800")
define blame = Character("Wolbleam", color="#576FFF")
define gino = Character("Wolpertgino", color="#00E340")
define pino= Character("Wolpino", color="#8811ED")
define sahai = Character("Wolsahai", color="#FF0000")
transform sx:
    xalign 0.0
    yalign 1.0
transform csx:
    xalign 0.3
    yalign 1.0
transform cdx:
    xalign 0.7
    yalign 1.0
transform dx:
    xalign 1.0
    yalign 1.0


# Il gioco comincia qui.

label start:
    scene bg intro
    play music intro

    "Benvenuto."
    
    python:
        name = renpy.input("Per favore, inserisci il nome del tuo personaggio (Default: Usbaldo)")
        if not name:
            name = "Usbaldo"

    "Grazie {color=#FFD800}[name]{/color}"
    "Che l'avventura abbia inizio..."

    scene bg forest
    play music forest

    player "Ah, che pomeriggio tranquillo..." 
    player "Fin troppo."
    player "Mi sono stancato di ammazzare lupi."
    player "Ci vorrebbe un bel dungeon..."
    player "Ma nessuno dei miei compagni di gilda è online"
    player "Vediamo se qualcuno sta cercando di formare un gruppo..."
    player "Trovati! E sono già in quattro, manco solo io. Mi aggiungo subito."

    show blame stand sorriso at csx
    blame "Ciao {color=#FFD800}[name]{/color}, io sono {color=#576FFF}Wolbleam{/color} e faccio parte dei Wolpertingers"
    player "Ciao io sono... beh lo sai già." 
    player "Hai detto... Wolpertingers?"
    blame "Sì, è la nostra gilda."
    player "Che nome curioso, da dove arriva?"
    show blame stand normale
    blame "È il nome di un animaletto dolcissimo, il Wolpertinger appunto." 
    blame "Ho un immagine vuoi vederla?"
    menu:
        "Ok.":
            jump wolperSi
        "No, grazie.":
            jump wolperNo

label wolperSi:
    player "Certo, sono curioso di sapere com..."
    scene bg wolpertinger2
    play sound jumpscare
    player "AAAAHHHH!"
    scene bg forest
    show blame stand sorriso at csx
    blame "Allora non è un amore?"
    player "hem... sì... dolcissimo ({i}Mamma mia che brutta roba...{/i})"
    show blame stand normale:
    jump wolperDone

label wolperNo:
    blame "Peccato è dolcissimo."
    jump wolperDone

label wolperDone:
    blame "Ma ecco che arrivano gli altri membri della gilda"
    show gino stand normale at cdx
    blame "Questo è {color=#00E340}Wolpertgino{/color}, il nostro cacciatore stiloso"
    gino "'ao"
    player "Ciao. Ma... Sei a piedi nudi?"
    show gino flex
    gino "Sì, no. Armatura figa, piace? Presa con queste scarpe strette, ora tolte, ma lancia lunga e allora cambio specializzazione, più danni."
    player "Cos...? Che ha detto?!"
    show blame stand imbarazzo
    blame "Hem... no, niente, lascia stare." 
    blame "A volte va interpretato."
    show blame stand normale
    show gino stand normale
    blame "Questo che è arrivato ora invece è il nostro stregone! Sempre l'ultimo..."
    #show pino stand basso at sx
    pino "Vorrei vedere te, se avessi metà delle gambe che hai!"
    pino "Maledetti spilungoni..."
    blame "Ti presento {color=#8811ED}Wolpino{/color}"
    player "Uh... dov'è? Io non vedo nessuno..."
    pino "Hey, torre di Kharazan, prova a guardare sotto le nuvole che hai intorno al cervello. Sono qui in basso."
    blame "Ah, aspetta... un bel incantesimo di levitazione..."
    blame "Là!"
    play sound levitazione
    show pino levita normale at sx
    blame "E il gioco è fatto!"
    pino "Umiliante..."
    player "ciao Wolpino, piacere."
    pino "Tutto tuo."
    blame "Bene, possiamo andare!"
    player "Ma.. Non ne manca uno?"
    show blame stand imbarazzo
    blame "..."
    blame "sì certo, il nostro tank... ecco..."
    blame "arriverà..."
    show sahai lontano behind gino, blame:
        xalign 0.9
        yalign 0.5
    sahai "({i}in lontananza{/i}) hey raga, dove siete?"
    player "{i}mmm.. che gruppo eterogeneo.{/i}"
    hide sahai lontano
    show blame stand normale
    blame "Allora che ne dici? Ti unisci a noi?"
    menu:
        "Sì, volentieri.":
            jump accettato
        "Grazie, ma mi sono ricordati che devo andare a pulire la cassetta del gatto.":
            jump end01

label end01:
    player "Grazie, ma mi sono ricordati che devo andare a pulire la cassetta del gatto."
    blame "Ah, ok, peccato. Sarà per la prossima volta"
    hide blame
    pino "Già, un vero peccato..."
    hide pino
    pino "Per te!"
    gino "In giro, figo, magari beccarsi. Sai dove armature? Bye"
    hide gino
    jump badend

label badend:
    scene bg forest
    play music forest
    "Resti solo con i tuoi pensieri."
    "E con la forte sensazione di aver scampato un enorme pericolo."
    "FINE"
    return

label accettato:
    player "Sì, volentieri."
    show blame stand sorriso
    blame "Fantastico!"
    blame "Dimmi, che ruolo vorresti avere nel gruppo?"
    jump sceltaruolo

label sceltaruolo:
    show blame stand normale
    show gino stand normale
    show pino levita normale
    menu:
        "Tank":
            jump tank
        "DPS":
            jump dps
        "Healer":
            jump healer

label tank:
    player "Sono un tank niente male."
    show blame stand sorriso
    blame "Oh, peccato!"
    show gino stand stupito
    show pino levita stupito
    blame "Abbiamo già un'ottimo tank!"
    show sahai lontano behind gino, blame:
        xalign 0.5   
        yalign 0.5
    show pino levita stupito
    sahai "({i}in lontananza{/i}) Ma dove sono finiti?"
    blame "Prova un altro ruolo"
    hide sahai
    jump sceltaruolo


label healer:
    player "Sono un discreto Healer."
    player "Con me non rischiate wipe."
    show blame stand paresi
    blame "..."
    hide blame
    hide pino
    hide gino
    "Wolbleam ti ha espulso dal gruppo"
    jump badend

label dps:
    show blame stand sorriso
    blame "Ottimo, proprio quello che ci serviva!"
    blame "Andiamo!"
    jump dungeon

label dungeon:
    scene bg dungeon
    play music battle1
    show pino guardia concentrato at sx
    pino "Ok, gente, siamo dentro."
    pino "Da questo momento tutti all'erta."
    show blame guardia concentrato at csx
    blame "Una pattuglia! Presto riepiloghiamo la tattica!"
    show gino guardia concentrato at cdx
    gino "Uno Io, arco, tu, destra, sinistra, spatush!"
    player "eh?!..."
    pino "No, aspetta {color=#00E340}Wolpertgino{/color}."
    pino "{color=#FF0000}Wolsahai{/color} attacca il capo."
    show sahai guardia concentrato at dx behind gino
    sahai "Pronta!"
    pino "{color=#00E340}Wolpertgino{/color} trappola congelante sulla guardia di destra."
    gino "Ok, trappola, lancio, ghiaccio. Tocca no."
    pino "Io e {color=#FFD800}[name]{/color} sulla guardia di sinistra."
    pino "E {color=#576FFF}Wolblame{/color} cura dalle retrovie."
    pino "Metto un teschio sul capo. La croce sulla guardia da attaccare e la luna su quella da congelare."
    pino "Pronti?"
    player "{i}Beh però, che team! Sono davvero organizzati.{/i}"
    gino "Guardia luna trappolata!"
    pino "VIA!"
    menu:
        "Attacca la guardia con l'icona a croce":
            jump attacca
        "Aspetta che attacchi il tank ":
            jump aspettatank

label attacca:
    "Un secondo dopo aver lanciato il tuo attacco a distanza sulla guardia senti una voce alle tue spalle..."
    sahai "Oh, guarda, un sasso da estrarre! Arrivo subito..."
    hide sahai
    show pino guardia paura
    show blame guardia paura
    show gino guardia paura
    "La pattuglia vi attacca in forze..."
    jump primoscontro

label aspettatank:
    "Attendi che il tank parta all'attacco, ma senti..."
    sahai "Oh, guarda, un sasso da estrarre! Arrivo subito..."
    hide sahai
    blame "Non preoccuparti {color=#FFD800}[name]{/color}, è normale."
    player "{i}Sarà...{/i}"
    show sahai guardia concentrato at dx behind gino
    sahai "Ecco ci sono. Quando volete."
    pino "Figurati fai pure con comodo..."
    pino "VIA!"
    hide sahai
    sahai "HAAAAAAAAIiiii..."
    show pino guardia paura
    show blame guardia paura
    show gino guardia paura
    "Il tank parte alla carica con un potente... attacco ad area!"
    "La trappola viene annullata e la pattuglia vi attacca in forze."
    jump primoscontro

label primoscontro:
#DISSOLVENZA TODO    
    scene bg black
    with fade
    scene bg dungeon
    with fade
    show pino guardia attacco at sx
    show blame guardia attacco at csx
    show gino guardia attacco at cdx
    pino "Presto, due DPS su una guardia e un DPS sull'altra!"
    blame "Sto consumando il mana troppo in fretta!"
    gino "Ricaricando speciali danni poco poco..."
    player "Eh?"
    pino "Eh?"
    blame "Eh?"
    show gino guardia paura
    gino "Aiuto aiutate! Vita finale!"
    show blame guardia paura
    blame "Mi attaccano, qualcuno mi aiuti!"
    menu:
        "Aiuta Wolpertgino":
            jump primoscontroHunter
        "Aiuta Wolbleam":
            jump primoscontroHealer

label primoscontroHunter:
    "Lanci il tuo colpo più potente sulla guardia che sta attaccando {color=#00E340}Wolpertgino{/color}."
    "La guardia canbia bersaglio e punta verso di te."
    "Ma non fai a tempo a preoccupartene che senti l'urlo di {color=#576FFF}Wolbleam{/color}"
    show blame stand spirito
    blame "Ahhhh! Sono mort... andata. Siete senza healer..."
    show pino stand spirito
    show gino stand spirito
    show sahai stand spirito at dx
    "Dopo 10 secondi siete tutti morti"
    jump wipe1

label primoscontroHealer:
    "Lanci il tuo colpo più potente sulla guardia che sta attaccando {color=#576FFF}Wolbleam{/color}."
    "La guardia cambia bersaglio e punta verso di te."
    show gino stand spirito
    "Intanto alle tue spalle senti le imprecazioni di {color=#00E340}Wolpertgino{/color} che viene abbattuto e il suo avversario punta su di te."
    show sahai guardia concentrato at dx behind gino
    "Ma {color=#FF0000}Wolsahai{/color} lo intercetta."
    "Il combattimento prosegue e dopo un minuto siete di nuovo in crisi."
    show gino guardia concentrato
    "Ma {color=#00E340}Wolpertgino{/color} è resuscitato e si riunisce alla battaglia."
    "Cade la prima guardia."
    "Cade la seconda."
    "E cade il capo. Finito!"
    show blame stand normale
    show pino stand normale
    show gino stand normale
    show sahai stand normale
    blame "Datemi qualche secondo per recuperare Mana."
    jump altriscontri

label wipe1:
    scene bg cimitero
    menu:
        "Riproviamoci!":
            jump riproviamoci
        "Abbandona subito questo gruppo di pazzi":
            jump badend

label riproviamoci:
    scene bg dungeon
    show blame guardia concentrato at csx
    show pino guardia concentrato at sx
    show gino guardia concentrato at cdx
    show sahai guardia concentrato at dx behind gino  
    pino "Va bene... questa volta niente rocce e niente attacchi ad area, chiaro?"
    sahai "Perché guardi me?"
    pino "Mah... Sarò strabico..."
    pino "Wolpertgino, trappola!"
    pino "Wolsahai, attacca!"
    show blame guardia attacco at csx
    show pino guardia attacco at sx
    show gino guardia attacco at cdx
    hide sahai 
    "Questa volta il piano funziona e tutto fila liscio."
    show blame stand maglia
    "Così liscio che l'healer non deve sofrzarsi più di tanto..."
    jump altriscontri

label altriscontri:
    scene bg black
    with fade
    "Così proseguite nel dungeon..."
    scene bg dungeon2
    with fade
    show blame guardia concentrato at csx
    show pino guardia concentrato at sx
    show gino guardia concentrato at cdx
    show sahai guardia concentrato at dx behind gino
    "con moltri altri combattimenti..."
    show blame guardia attacco at csx
    show pino guardia attacco at sx
    show gino guardia attacco at cdx
    hide sahai
    "alcuni finiti bene..."
    show blame stand spirito at csx
    show pino stand spirito at sx
    show gino stand spirito at cdx
    show sahai stand spirito at dx
    "e altri meno..."
    show blame guardia concentrato at csx
    show pino guardia concentrato at sx
    show gino guardia concentrato at cdx
    show sahai guardia concentrato at dx behind gino
    "finché..."

#BOSS
    scene bg ragnaros
    play music battle2
    show blame stand normale at csx
    show pino stand normale at sx
    show gino stand normale at cdx
    show sahai stand normale at dx
    pino "Ok, siamo al boss finale."
    pino "Massima concentrazione."
    pino "Cosa sappiamo su questo boss?"
    gino "Abilità speciali dopo tre volte colpo bua vicino, saltare, ma con sfere verdi tutti scappa scappa, poi tanti cosi."
    pino "Ooookey... beh, fate del vostro meglio"
    show blame guardia concentrato at csx
    show pino guardia concentrato at sx
    show gino guardia concentrato at cdx
    show sahai guardia concentrato at dx behind gino
    pino "Pronti?"
    sahai "YAAAAAhhh"
    show pino guardia paura
    show blame guardia paura
    show gino guardia paura
    hide sahai
    pino "...via?..."

    scene bg cimitero
    show blame stand spirito at csx
    show pino stand spirito at sx
    show gino stand spirito at cdx
    show sahai stand spirito at dx
    pino "È semplice..."
    pino "Prima c'è il 'Pronti'..."
    pino "Poi c'è il 'Via'..."
    pino "E DOPO si parte. Tutto chiaro?"
    sahai "Non ho tempo per il 'Pronti'. Non si può fare 'Via' subito?"
    pino "..."
    menu:
        "Ne hai abbastanza di questo gruppo di incapaci e decidi di abbandonare!":
            jump badend
        "Ok, riproviamoci...":
            jump insisti1

label insisti1:
    scene bg ragnaros
    show blame guardia concentrato at csx
    show pino guardia concentrato at sx
    show gino guardia concentrato at cdx
    show sahai guardia concentrato at dx behind gino
    pino "Pr... hem, VIA!"
    sahai "YAAAAAhhh"
    hide sahai
    show gino guardia paura
    gino "COLPO BUA!"
    show blame guardia paura
    show pino guardia paura
    pino "Cos...?"

    scene bg cimitero
    show blame stand spirito at csx
    show pino stand spirito at sx
    show gino stand spirito at cdx
    show sahai stand spirito at dx
    pino "Ok, ora sappiamo cos'è il 'colpo bua'... se lo conosci..."
    menu:
        "Ora sì che ne hai abbastanza di questo gruppo di incapaci e decidi di abbandonare!":
            jump badend
        "Ok, riproviamoci...":
            jump insisti2

label insisti2:
    scene bg ragnaros
    show blame guardia concentrato at csx
    show pino guardia concentrato at sx
    show gino guardia concentrato at cdx
    show sahai guardia concentrato at dx behind gino
    pino "VIA!"
    sahai "Hey guarda che strane sfe..."
    show sahai stand spirito at dx
    sahai "..."
    show gino guardia paura
    show blame guardia paura
    show pino guardia paura
    gino "SFERE VERDI!"

    scene bg cimitero
    show blame stand spirito at csx
    show pino stand spirito at sx
    show gino stand spirito at cdx
    show sahai stand spirito at dx
    pino "..."
    gino "Io avevo detto tutto prima di adesso."
    pino "Già, ma evidentemente in quel momento non ci funzionava google translator..."
    gino "Detto colpo bua, detto sfere verdi, nessuno orecchia me….."
    menu:
        "No, davvero, adesso ne hai proprio abbastanza di questo gruppo di incapaci e decidi di abbandonare!":
            jump badend
        "Ok, riproviamoci...":
            jump insisti3

label insisti3:
    scene bg ragnaros
    show blame guardia concentrato at csx
    show pino guardia concentrato at sx
    show gino guardia concentrato at cdx
    show sahai guardia concentrato at dx behind gino
    pino "VIA!"
    show blame guardia attacco at csx
    show pino guardia attacco at sx
    show gino guardia attacco at cdx
    hide sahai
    gino "COLPO BUA!"
    sahai "COLPO EVITATO!"
    gino "SFERE VERDI!"
    pino "SFERE NEUTRALIZZATE!"
    gino "COSI BRUCOSI!"
    pino "COSI BRU..."
    show pino guardia paura
    pino "Cosi cosa?!"

    scene bg cimitero
    show blame stand spirito at csx
    show pino stand spirito at sx
    show gino stand spirito at cdx
    show sahai stand spirito at dx
    pino "..."
    pino "Non ci avevi detto dei cosi brucosi..."
    gino "Detto sempre, detto tutto, prima di prima. Nessuna padigliona."
    pino "Gesù..."  
    menu:
        "A questo punto insistere sarebbe da masochisti e abbandoni!":
            jump badend
        "Ok, riproviamoci...":
            jump insisti4

label insisti4:
    scene bg ragnaros
    show blame guardia attacco at csx
    show pino guardia attacco at sx
    show gino guardia attacco at cdx
    show sahai guardia concentrato at dx behind gino
    "Così riprovate..."
    scene bg cimitero
    show blame stand spirito at csx
    show pino stand spirito at sx
    show gino stand spirito at cdx
    show sahai stand spirito at dx
    "ancora..."
    scene bg ragnaros
    show blame guardia attacco at csx
    show pino guardia attacco at sx
    show gino guardia attacco at cdx
    show sahai guardia concentrato at dx behind gino
    "...e ancora..."
    scene bg cimitero
    show blame stand spirito at csx
    show pino stand spirito at sx
    show gino stand spirito at cdx
    show sahai stand spirito at dx
    "...e ancora..."

    scene bg ragnaros
    show blame guardia attacco at csx
    show pino guardia attacco at sx
    show gino guardia attacco at cdx
    hide sahai
    "...e ancora..."
    pino "...ATTENTI, LE SFERE! Ci penso io..."
    show pino stand spirito at sx
    pino "Sfere neutralizzate, ma io sono fuori gioco."
    pino "{color=#00E340}Wolpertgino{/color} tu e {color=#FFD800}[name]{/color} pensate ai cosi brucosi, {color=#FF0000}Wolsahai{/color}, attenta al colpo bua!"
    show gino stand spirito at cdx
    gino "Brucosi non brucano più!"
    pino "Va bene così, bravo {color=#00E340}Wolpertgino{/color}. {color=#FF0000}Wolsahai{/color}, tira giù quel maledetto boss!"
    blame "La salute del tank scende troppo velocemente, non riesco a curarla abbastanza in fretta!"
    sahai "Ci sono quasi… ci sono quasi… ahhhhh!"
    show sahai stand spirito at dx
    sahai "Niente da fare. Mancava pochissimo ma è ancora in piedi."
    "Siete rimasti tu e l'healer. Tu sei lontano e hai pochissima salute."
    "Il boss ti punta ma non sai se potrai colpirlo prima che lui copisca te."
    pino "{color=#576FFF}Wolbleam{/color}, curalo, presto! Così gli da il colpo di grazia."
    sahai "No, lascia perdere {color=#FFD800}[name]{/color} e attacca tu il boss!"
    gino "E uguale mc quadro!"
    "tutti" "Eeeh?!"
    blame "Aiuto, cosa devo fare?"
    menu:
        "Mai sentito di un healer che abbatte un boss. Dille di curarti!":
            jump healerCura
        "Con una banda di pazzi ci vuole un po' di pazzia. Dille di attaccare!":
            jump healerAttacca

label healerCura:
    player "Presto {color=#576FFF}Wolbleam{/color}, curami!"
    "{color=#576FFF}Wolbleam{/color} ti cura ma appena entri nel range del boss quello ti tira un colpo mortale e ti stende"
    show blame guardia concentrato
    "{color=#576FFF}Wolbleam{/color} ha esaurito il mana curandoti e non può più attaccare… Il boss elimina anche lei."
    scene bg cimitero
    show blame stand spirito at csx
    show pino stand spirito at sx
    show gino stand spirito at cdx
    show sahai stand spirito at dx
    pino "Peccato... Questa volta c'eravamo quasi"
    pino "Riproviamo?"
    menu:
        "Ormai che te lo dico a fare...? (Abbandona)":
            jump badend
        "ok riproviamoci":
            jump insisti4

label healerAttacca:
    player "{color=#576FFF}Wolbleam{/color} non preoccuparti di me, attacca il boss!"
    "Il boss ti raggiunge e ti abbatte con un colpo solo."
    blame "PRENDI QUESTO!"
    "Il boss viene colpito dall'attacco di Wolblame e… "
    "..finalmente muore!"
    show blame stand normale at csx
    show pino stand normale at sx
    show gino stand normale at cdx
    show sahai stand normale at dx
    sahai "Brava healer!"
    show gino flex
    gino "YEAH! Wolpertinger  1, Boss 0"
    pino "Veramente sarebbe Wolpertinger 1, Boss 15... Ma va bene così."
    show gino stand normale at cdx
    blame "Grazie, grazie"
    pino "Saccheggiate e andiamocene da qui."

    scene bg forest
    play music forest
    show blame stand normale at csx
    show pino stand normale at sx
    show gino stand normale at cdx
    show sahai stand normale at dx
    blame "Bene {color=#FFD800}[name]{/color}, grazie dell'aiuto."
    pino "mmm... sì, non male. Ci hai rallentato un po', ma alla fine te la sei cavata."
    gino "Wolpertinger onorario!"
    sahai "oh guarda un sasso…."
    hide sahai
    show gino flex
    gino "Hai visto che armatura figa? Ciao!"
    hide gino
    pino "Alla prossima"
    hide pino
    blame "ciao {color=#FFD800}[name]{/color}, alla prossima"
    hide blame
    "Rimani solo. Un po' stordito forse ma convinto di aver conosciuto persone simpatiche."
    "Magari non esattamente dei pro dei dungeons... ma ti sei divertito"
    "E ora… che si fa? Cerchiamo qualche lupo..."
    "FINE"
return

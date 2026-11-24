---
title: Incidenskezelési szabályzat
description: Eljárások a biztonsági incidensek észlelésére, kezelésére és az azokat követő helyreállításra
---

# Incidenskezelési szabályzat

## 1. Cél

Ez a szabályzat rögzíti az információbiztonsági incidensek azonosításának, kezelésének és megoldásának keretrendszerét. Következetes és eredményes megközelítést biztosít az incidensek kezeléséhez, a lehető legkisebbre csökkentve a hatást és lehetővé téve a gyors helyreállítást.

## 2. Hatály

A szabályzat hatálya kiterjed minden olyan információbiztonsági incidensre, amely a szervezet rendszereit, adatait, munkatársait vagy működését érinti, többek között a következőkre:
- Jogosulatlan hozzáférés rendszerekhez vagy adatokhoz
- Kártékony kód okozta fertőzések
- Adatszivárgás vagy adatvesztés
- Szolgáltatásmegtagadással járó támadások
- Pszichológiai manipuláción alapuló támadások
- A fizikai biztonság információs eszközöket érintő megsértése

## 3. Incidensek besorolása

### 3.1 Súlyossági szintek

| Szint | Leírás | Példák |
|-------|-------------|----------|
| Kritikus | Jelentős hatás az üzleti működésre vagy az adatokra | Adatszivárgás, zsarolóvírus, teljes rendszerleállás |
| Magas | Azonnali figyelmet igénylő, komoly hatás | Jogosulatlan hozzáférés érzékeny adatokhoz, részleges leállás |
| Közepes | Mérsékelt hatás, korlátozott kiterjedéssel | Kártékony kód egyetlen rendszeren, szabályszegés |
| Alacsony | Csekély hatás, adatvesztés nélkül | Sikertelen behatolási kísérlet, kisebb eltérés a szabályzattól |

## 4. Incidenskezelési szakaszok

### 4.1 Felkészülés
- Meghatározott szerepkörökkel és felelősségekkel rendelkező incidenskezelő csapat fenntartása
- A csapattagok képzésének biztosítása és rendszeres gyakorlatok tartása
- Naprakész elérhetőségi listák és eszkalációs eljárások fenntartása
- Észlelő és felügyeleti eszközök telepítése és karbantartása

### 4.2 Észlelés és elemzés
- A rendszerek és a hálózatok felügyelete a kompromittálódásra utaló jelek feltárására
- A riasztások elemzése a kiterjedés és a súlyosság megállapítása érdekében
- A kezdeti megállapítások dokumentálása és az incidens besorolása
- Az illetékes érdekelt felek értesítése a súlyosság alapján

### 4.3 Elszigetelés
- Rövid távú elszigetelés végrehajtása a közvetlen kár korlátozására
- A bizonyítékok megőrzése a forenzikus elemzéshez
- Szükség szerint hosszú távú elszigetelési intézkedések bevezetése
- Az érdekelt felek tájékoztatása az elszigetelés állapotáról

### 4.4 Felszámolás
- A kiváltó ok azonosítása és megszüntetése
- A kártékony kód, a jogosulatlan hozzáférés vagy más fenyegetések eltávolítása
- A kihasznált sérülékenységek javítása frissítéssel
- Annak ellenőrzése, hogy a fenyegetést teljesen eltávolították

### 4.5 Helyreállítás
- Az érintett rendszerek visszaállítása tiszta biztonsági mentésekből
- A rendszerek integritásának ellenőrzése az éles üzembe való visszahelyezés előtt
- A visszaállított rendszerek felügyelete az ismétlődő problémákra utaló jelek feltárására
- A működés fokozatos helyreállítása megerősített felügyelet mellett

### 4.6 Incidens utáni felülvizsgálat
- Incidens utáni felülvizsgálat lefolytatása 5 munkanapon belül
- A levont tanulságok és az ajánlások dokumentálása
- A szabályzatok, az eljárások és a kontrollok szükség szerinti frissítése
- A lényeges megállapítások megosztása az illetékes csapatokkal

## 5. Bejelentési követelmények

- Minden feltételezett incidenst azonnal be kell jelenteni a biztonsági csapatnak
- A kritikus és a magas súlyosságú incidenseket 4 órán belül jelenteni kell a felső vezetésnek
- A hatósági bejelentéseket az előírt határidőn belül meg kell tenni
- Az érintett személyeket a jogszabályi előírások szerint értesíteni kell

## 6. Szerepkörök és felelősségek

### 6.1 Incidenskezelő csapat
- Az incidensek kivizsgálásának vezetése és koordinálása
- Az elszigetelésre és a felszámolásra vonatkozó döntések meghozatala
- Incidensjelentések és ajánlások készítése

### 6.2 Minden munkavállaló
- A feltételezett incidensek haladéktalan bejelentése
- Együttműködés az incidensek kivizsgálásában
- Az incidenskezelő csapat utasításainak követése

### 6.3 Vezetés
- Erőforrások és támogatás biztosítása az incidenskezeléshez
- Az incidens hatásával kapcsolatos üzleti döntések meghozatala
- A külső feleknek szóló kommunikáció jóváhagyása

## 7. Bizonyítékok kezelése

- A bizonyítékokat a bevált forenzikus gyakorlatok szerint kell összegyűjteni és megőrizni
- A felügyeleti láncot fenn kell tartani és dokumentálni kell
- A bizonyítékokat biztonságosan kell tárolni, és a jogszabályi követelmények szerint kell megőrizni

## 8. Kommunikáció

- A belső kommunikációnak a kialakított eszkalációs eljárásokat kell követnie
- A külső kommunikációt (média, hatóságok, ügyfelek) a felhatalmazott szóvivőkön keresztül kell koordinálni
- A kommunikációs sablonokat karban kell tartani, és rendszeresen frissíteni kell

## 9. A szabályzat felülvizsgálata

A szabályzatot legalább évente, valamint minden jelentős biztonsági incidens után felül kell vizsgálni. Az incidenskezelési tervet évente legalább kétszer asztali gyakorlattal kell tesztelni.

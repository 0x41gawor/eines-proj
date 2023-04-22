# Intro

Na rzecz projektu stworzymy komponent POX o nazwie `dzienciol.py`, który będzie implementował funkcjonalności wymagane w projekcie.

# Podjęte decyzje, poczynione założenia

## Intent model

```kotlin
class Inent{
  	var FROM: enum{H1, H2, H3}
	var TO: enum{H4,H5,H6}
	var LIMIT: Int 
}

```

Np.

```
Intent(FROM: H1, TO: H5, LIMIT: 60)
```

Reprezentuje Intent, który mówi, że dla flow H1->H5 max delay ma wynosić 60ms.

## Network policies

Network Policies mają load balancować ruch. Nasz load balancer będzie zachowywał się tak, że:

Defaultowo żadne flow* nie ma przypisanego route'a**. W momencie kiedy jakieś flow zaczyna być niezerowe (np. walniemy ping), to w Controllerze pojawi się wiadomość PACKET_IN. Naszym zadaniem jest teraz rozdawać rouety dla przychodzących flow, że każdy route będzie miał w miarę możliwość po równo flow'ów na sobie. Jak to zrobić?

Ustawiamy licznik dla każdego route'a i dajemy wartość 0. Przychodzi flow, to jak jest remis, dajemy na Route1 (do S1-S2). Potem robimy tak, żeby max róznica między licznikiem dla każdego route;a wynosiła 1. Cały ten algorytm będzie mieli w jednej funkcji, dla której triggerem może być albo PACKET_IN albo INTENT_IN lub INTENT_REROUTE. Czyli jak przyjdzie Intent i jego działanie nam "namiesza", to znaczy zrobi gdzieś różnicę 2, to te defaultowe flowy, musimy zrearanżować, żeby było git. Tak samo jak trzeba będzie zrerutować flow sterowane przez Intent (bo ruch w sieci zrobił tak, że obecna jego ścieżka już nie spełnia wymagań), to też trzeba będzie triggerować NetworkPolicer.

> *Jakie mogą być flow wgl? H1-H4, H1-H5, H1-H6, H2-H4, H2-H5, H2-H6, H3-H4, H3-H5H3-H6
>
> ** Jaki może być route wgl? S1-S2, S1-S3, S1-S4.
>
> Topologia
>
> <img src="img/topology.png" style="zoom:75%;" />

Czyli wybieramy tę opcję

![](img/2.png)

## One flow at a time

![](img/3.png)

Mimo, iż druga opcja jest dużo bardziej naturalna, to programistycznie o niebo łatwiej będzie zrobić *basic*.

W zmiennej będziemy trzymać aktualnie intented flow oraz jego delay limit. 

# Architektura dzienciola

`dzineciol.py` to produkt, który będziemy tworzyć w ramach projektu

- Network Policer
  - będzie rerutował defaultowe flowy (flow moze być albo intented albo default) tak aby każdy route miał po równo flow
- Intent Policer
  - będzie monitorował i rerutował Intented flow a następnie triggerował Network Policer
- Intent Handler
  - będzie przyjmował request na intent i triggerował Intent Policer
- Network Monitor
  - Będzie monitorował jakie są delaye na rutach i ew. triggerował Intent jak wykryje nie spełnienie wymagań

# Release history of dzienciol.py

## Release 1

Kod dzienciola jest bardzo prosty, w zasadzie stanowi on podzbiór kodu `routing_controller.py`. Zachowana jest jedynie funkcjonalność handlowania połączeń ze switchami i wypisywania tego na konsolę. 

![](img/1.png)

Tak, więc `dzienciol.py` posiada tylko funckję `_handle_ConnectionUp` oraz launch, które tę funkcję rejestruje w POX jako handler eventu "ConnectionUp".

Jak narazie `dzienciol.py` nie wstawia żadnych table flow entries do switchów wobec tego w sieci `topology.py` nie działają pingi pomiędzy hostami. 

Następnym krokiem jest sprawić, aby `dzienciol.py` wstawił jakikolwiek flow entry do switcha  i żeby dało się spingować jakikolwiek host.

> Tak się zastanawiam, że chyba skoro tylko lewa strona switchów ma obsługiwać intenty, to można na PACKET_IN dać jakiś behavior dla prawej strony i wgl niech defaultowo wszystko będzie na PACKET_IN jakimś hardcoded routingiem, a dopiero jak przyjdzie intent to będą zmiany.

# Future goals

1. Default flows 
2. Network Policer
3. Intent Handler
4. Network Monitor
5. Intent Policer

## 1. Default flows

### AS IS

Obecnie controller żadnemu ze switchy nie wpisuje żadnych table flow entries wobec tego ping między hostami nie działają.

### TO BE

Chcemy, aby każdy ze switchy otrzymał defaultowe ścieżki.

Tzn. gdy pojawi się pakiet i switch wyśle do dzienciola PACKET_IN, to żeby dzienciol mu odpowiedział defaultowym pathem. Narysujmy te ścieżki na topologii.

![](img/4.png)

### Implementacja

Na to to się przekłada w flow table

![](img/5.png)

## 2. Network Policer

To będzie tak, że będą przychodzić flow. A my te flowy będziemy przypisywać do tego którymi ścieżkami mają iść. Network Policer będzie przypisywał, które flow ma iść którą ścieżką. Komponent FlowRouteApplier będzie actually przypisywał flow na route, czyli w switch'ach instalował flow table entries. Będzie miał metodkę: `install(flow, route)`, która będzie wysyłać do S1 i S5 FLOW_TABLE_MOD tak, żeby dane flow Hn-Hm poleciało danym routem.

Jakie mamy route'y i jakie mamy flow.

![](img/6.png)

Jeśli chodzi o switche S2, S3, S4 to one są tranzytowe, mają po prostu przekazywać pakiety z portu 1 na 2 i vice versa. 

Jeśli chodzi o switch S1,S5 to one muszą w obie strony rozróżniać te 9 flow i wiedzieć jaki jest path dla nich, dla tych flow tzn.

Switche S1 i S5 będą miały kilka wpisów statycznych są to wpisy, które mówią jak kierować ruch do hostów //ruch z sieci

```python
------- RUCH Z SIECI
S1:
packet.dst_addr == "10.0.0.1" --> out_port = 1
packet.dst_addr == "10.0.0.2" --> out_port = 2
packet.dst_addr == "10.0.0.3" --> out_port = 3
S5:
packet.dst_addr == "10.0.0.4" --> out_port = 4
packet.dst_addr == "10.0.0.5" --> out_port = 5
packet.dst_addr == "10.0.0.6" --> out_port = 6
```

Czyli wpisy dla S2, S3 i S4 oraz statyczne dla S1 i S5 Network Policer wykonuje takie same.

Gdy przyjdzie PACKET_IN od s2, s3, s4 to Network Policer ma na to metodke `installTransitRouting` a na static S1 i S4 ma metodke `installClientRouting(switch)`, obie te instalki zwracają wiadomość, którą wysyłasz. 

Dopiero dynamiczne jest to co się dzieję kiedy S1 i S5 forwardują coś "w środek sieci" do switchów S2, S3 i S4.

Więc jak będzie wyglądała ta metoda od dynamicznego Flow Table Mod?

```python
------- RUCH DO SIECI
def install(Hn: n, Hm: m, Routep: p)
	S1
    in_port == n AND dst_addr == "10.0.0.m" ---> out_port = p+3 // w prawo
    S5
    in_port == m AND dst_addr == "10.0.0.n" ---> out_port = p   // w lewo
```

ta metodka zwraca dwie msg i je wysyłasz do S1 i S5.

### Kiedy triggerowany jest Network Policer?

Kiedy przychodzi nieznane flow. Czyli Packet IN od S1 lub S5. 

Network Policer musi na tej podstawie zidentyfikować flow. A następnie wybrać mu sciezke i zainstalować mu ją. 

Network Policer to musi być klasa, a w niej licznik flow dla każdego Route. `Route1FlowCount, Route2FlowCount, Route3FlowCount`. Będzie metoda `SelectRoute()`, która na podstawie tych zmiennych wybierze ścieżke. 

Też fajnie by było jakby Network Policer pamiętał jakie flow przypisał to jakiej ścieżki. 

Żeby reprezentować Flow przyda sie jakaś klasa.

A Network Policer niech trzyma mape flow<->route

### Identyfikacja flow

Flow mogą originate tylko z H1, H2 i H3 -> rozponawanie flow będzie tylko w S1.

```python
a.in_port ---> Hn
a.dst_address ---> Hm
flow = Flow(n,m)
route_for_flow = select_route(flow) // select route ma mechanike, która wybiera najmniej obciążoną ścieżkę
if (route!=None) //jak flow juz ma route (ale to się chyba nie bedzie zdarzac) to zwracamy None
flow_route_map.add(flow, route)
install(flow, route) // instalacja jest zarówno na S1 jak i S5
```

### Logi

```python
Network Policer: New Flow H1-H4 detected, route 1 assigned
Network Policer: No. of flow on routes, Route1: 1, Route2: 1, Route3: 0
Network Policer: ActiveFlows [{H1-H4,Route1}, {H2-H5,Route2}]
```




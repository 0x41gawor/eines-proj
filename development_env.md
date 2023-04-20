# Przygotowanie

Zróbcie sobie chłopaki tak

Na pulpicie klon repo

```sh
git clone https://github.com/0x41gawor/eines-proj
```

i wszystkie pliki `.py` trzeba skopiować z repo do folderu `~/pox`

> Na ten moment są to pliki:
>
> - `dzienciol.py`
> - `dzienciol_lib.py`

Zainstalujcie se Visual Studio Code, że móc w nim programić

```sh
sudo snap install --classic code
```

No i też jak będziecie coś zmieniać w `dzienciol.py` (i innych) w folderze `pox` to, żeby jednocześnie to się zmieniało w folderze `eines-proj` to robicie hard linka

```sh
cd ~/pox
ln dzienciol.py ~Desktop/eines-proj/dzienciol.py
ln dzienciol_lib.py ~Desktop/eines-proj/dzienciol_lib.py
```

# Uruchomienie controllera i sieci

## Run

### Mininet

```sh
cd ~/Desktop/eines-proj
sudo python topology.py
```

### Pox

```sh
cd ~/pox
sudo python ./pox.py dzienciol &
```

## Kill

### Mininet

```
mininet> exit
sudo mn -c
```

### Pox

Ofc najpierw ctrl+c

```
ps -aux | grep pox
sudo kill -9 <pid>
sudo kill -9 <pid>
```

## Debugowanie

Przydatna komenda to

```sh
sudo ovs-ofctl dump-flows s1
```
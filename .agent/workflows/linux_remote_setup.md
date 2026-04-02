---
description: Guia completo para configurar acesso remoto ao Ubuntu (Dual Boot) a partir do Windows, tanto nativo quanto via VS Code.
---

# 🐧 Guia de Configuração de Acesso Remoto (Windows -> Ubuntu)

Este guia cobre como configurar sua máquina Linux (Ubuntu) para aceitar conexões SSH e como acessá-la de outro computador Windows na mesma rede.

---

## 🏗️ PARTE 1: Preparando o Ubuntu (Servidor)

Faça isso na máquina que está rodando o Ubuntu.

### 1. Instalar o Servidor SSH
1.  Abra o Terminal (`Ctrl+Alt+T`).
2.  Atualize e instale o pacote:
    ```bash
    sudo apt update
    sudo apt install openssh-server -y
    ```

### 2. Configurar o Firewall (Crucial!)
Muitas falhas acontecem aqui. Precisamos abrir a porta 22.
```bash
sudo ufw allow ssh
sudo ufw enable
```
*(Se perguntar se deseja continuar, digite `y`)*.

Verifier se está ativo:
```bash
sudo ufw status
# Deve aparecer: 22/tcp ALLOW Anywhere
```

### 3. Descobrir o IP da Máquina
Você precisa saber o endereço IP local do Ubuntu.
```bash
hostname -I
```
O resultado será algo como: `192.168.0.25`. Anote este número.

---

## 💻 PARTE 2: Acesso Nativo (Do Windows)

Como acessar o terminal do Linux usando apenas o Windows (PowerShell ou CMD), sem instalar nada.

1.  No computador Windows, abra o **PowerShell** ou **Prompt de Comando**.
2.  Digite o comando SSH padrão:
    ```powershell
    ssh usuario_linux@192.168.xx.xx
    ```
    *(Substitua `usuario_linux` pelo nome do seu usuário no Ubuntu e o IP pelo que você anotou).*

3.  **Primeira Conexão:** Vai aparecer uma mensagem sobre "authenticity of host".
    *   Digite `yes` e dê Enter.
4.  **Senha:** Digite a senha do seu usuário Linux (ela não aparecerá na tela enquanto você digita).

Se conectar, parabéns! Você está controlando o terminal do Linux de dentro do Windows. 🎉

---

## 🆚 PARTE 3: Configurando o VS Code (Dev Environment)

Isso transforma o VS Code do Windows em uma interface para o Linux. Você edita arquivos como se estivessem locais, mas roda o código na máquina remota.

### 1. Instalar Extensão
1.  Abra o VS Code no Windows.
2.  Vá na aba de Extensões (`Ctrl+Shift+X`).
3.  Procure por **"Remote - SSH"** (Microsoft) e instale.

### 2. Conectar
1.  Pressione `F1` (ou `Ctrl+Shift+P`) para abrir a paleta de comandos.
2.  Digite e selecione: `Remote-SSH: Connect to Host...`
3.  Selecione **"Add New SSH Host..."**.
4.  Digite o comando de conexão:
    ```
    ssh usuario_linux@192.168.xx.xx
    ```
5.  O VS Code vai pedir para salvar a configuração. Escolha o primeiro arquivo que aparecer (geralmente `C:\Users\voce\.ssh\config`).

### 3. Usar
1.  Pressione `F1` novamente e selecione `Remote-SSH: Connect to Host...`.
2.  O IP que você configurou vai aparecer na lista. Clique nele.
3.  Uma nova janela do VS Code abrirá. Ele pedirá a senha do Linux (uma vez).
4.  Pronto!
    *   Vá em **File > Open Folder**. Você verá as pastas do Linux (`/home/usuario/...`), não as do Windows.
    *   Abra o terminal (`Ctrl+'`) e você verá que é o terminal `bash` do Ubuntu.

---

## 🔧 Dica Pro: Fixar o IP (Opcional, mas Recomendado)
Roteadores domésticos trocam o IP dos dispositivos de vez em quando (DHCP). Para evitar ter que descobrir o IP todo dia:
1.  No Ubuntu, vá em **Settings > Wi-Fi (ou Network)**.
2.  Clique na engrenagem ao lado da conexão.
3.  Vá na aba **IPv4**.
4.  Mude de "Automatic (DHCP)" para **Manual**.
5.  Address: `192.168.0.50` (escolha um número alto para não conflitar).
6.  Netmask: `255.255.255.0`.
7.  Gateway: O IP do seu roteador (geralmente `192.168.0.1`).
8.  DNS: `8.8.8.8` (Google) ou o IP do roteador.

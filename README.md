# ProjectIA

Aplicativo desktop em Python para enviar perguntas à API da OpenAI e ler as respostas em uma interface gráfica feita com Tkinter. O projeto tem finalidade didática e separa a interface, a configuração e o acesso ao serviço para facilitar seu estudo e manutenção.

## Funcionalidades

- Interface em português para escrever perguntas e visualizar respostas.
- Validação de perguntas vazias e limite de 200 caracteres por envio.
- Requisições executadas em segundo plano para manter a janela responsiva.
- Modelo configurável por variável de ambiente.
- Mensagens para problemas de configuração, conexão e acesso à API.
- Histórico visual mantido somente durante a execução do aplicativo.

Cada pergunta é uma requisição independente: as mensagens anteriores exibidas na janela não são enviadas como contexto das próximas respostas. O aplicativo não salva conversas em arquivos ou banco de dados.

O limite de 200 caracteres considera o texto após remover espaços externos; quebras de linha internas contam. Cada resposta tem limite de 600 tokens de saída. Se a API indicar que interrompeu uma resposta pelo limite, o aplicativo sinaliza essa condição junto ao texto recebido.

## Pré-requisitos

- Python **3.11 ou posterior**.
- Tkinter e Tcl/Tk disponíveis na instalação do Python.
- Conexão com a internet para utilizar a API.
- Chave de API da OpenAI e acesso ao modelo configurado.
- Conta da API com os limites e a cobrança necessários ao uso pretendido.

A plataforma de API e o ChatGPT possuem sistemas de faturamento separados. Confira os créditos, os limites e a cobrança da organização usada pela chave na [orientação oficial de faturamento](https://help.openai.com/en/articles/9039756-managing-billing-for-chatgpt-and-the-api-platform). Os valores dependem do modelo e do uso; consulte os [preços da API](https://openai.com/api/pricing/) antes de enviar requisições.

## Instalação

Clone o repositório e entre na pasta do projeto:

```sh
git clone https://github.com/masterdeshon/ProjectIA.git
cd ProjectIA
```

Os comandos abaixo utilizam diretamente o Python do ambiente virtual, sem exigir sua ativação no terminal.

### Windows com PowerShell

Confirme que a versão exibida é 3.11 ou posterior:

```powershell
py -3 --version
py -3 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -e .
Copy-Item .env.example .env
```

### Linux ou macOS

Confirme que a versão exibida é 3.11 ou posterior:

```sh
python3 --version
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .
cp .env.example .env
```

Se o arquivo `.env` já existir, preserve sua configuração e edite-o diretamente em vez de substituí-lo.

## Configuração

Na raiz do projeto, abra o arquivo `.env` em um editor de texto e preencha:

```dotenv
OPENAI_API_KEY=sua_chave_aqui
OPENAI_MODEL=gpt-4.1-mini
```

| Variável | Uso |
| --- | --- |
| `OPENAI_API_KEY` | Chave obrigatória para autenticar as requisições. |
| `OPENAI_MODEL` | Identificador do modelo. O padrão do aplicativo é `gpt-4.1-mini`. |

Use um modelo disponível para sua organização e compatível com a Responses API. A escolha do modelo pode alterar os custos e o comportamento das respostas.

O aplicativo lê o `.env` da pasta atual, por isso execute os comandos na raiz do projeto. Variáveis já definidas no ambiente têm prioridade sobre o arquivo. Reinicie o aplicativo após alterar a configuração.

O arquivo `.env` contém configuração local e deve permanecer fora do Git. Compartilhe apenas o modelo [`.env.example`](.env.example), sem uma chave real.

## Executar

Na pasta do projeto, execute o comando correspondente ao seu sistema:

**Windows:**

```powershell
.venv\Scripts\python -m projectia
```

**Linux ou macOS:**

```sh
.venv/bin/python -m projectia
```

Após instalar o pacote, também é possível usar o comando `projectia` pelo ambiente virtual. Escreva uma pergunta com até 200 caracteres e envie-a pela interface. A resposta depende da disponibilidade da conexão, do serviço e do modelo configurado.

## Organização do repositório

```text
ProjectIA/
├── .env.example          # Exemplo de configuração sem credenciais
├── .github/workflows/    # Verificações automatizadas
├── src/projectia/        # Código do aplicativo
├── tests/                # Testes automatizados
├── pyproject.toml        # Dependências e configuração do pacote
├── CONTRIBUTING.md       # Orientações para contribuir
└── README.md
```

A integração utiliza o SDK oficial da OpenAI e a Responses API. As dependências são declaradas no [`pyproject.toml`](pyproject.toml).

## Testes e qualidade de código

Instale as dependências de desenvolvimento:

**Windows:**

```powershell
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m ruff format --check .
```

**Linux ou macOS:**

```sh
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
```

Os testes automatizados utilizam simulações do serviço e não precisam de uma chave real nem fazem requisições pagas. Eles não substituem a conferência manual da janela no sistema operacional utilizado. Um envio manual com uma chave válida realiza uma chamada real à API e pode gerar cobrança.

Os testes da janela usam Tkinter real com a janela oculta. Se o módulo `tkinter` estiver instalado, mas o interpretador Tcl/Tk ou a sessão gráfica estiver indisponível, esses cenários são marcados como ignorados (`skipped`). Os testes da configuração, do cliente e do executor não abrem janelas; o módulo `tkinter` continua sendo um pré-requisito para importar a interface e seu executor.

## Dados enviados ao serviço

Ao enviar uma pergunta, o aplicativo transmite seu texto e a configuração da requisição à API da OpenAI, autenticando o acesso com a chave configurada. O histórico visual anterior não acompanha os próximos envios.

O aplicativo não oferece armazenamento permanente de conversas. O tratamento dos dados pelo serviço externo segue os [controles de dados da API da OpenAI](https://developers.openai.com/api/docs/guides/your-data); a ausência de gravação local não define a retenção do provedor. Utilize exemplos fictícios ao demonstrar o projeto.

## Solução de problemas

| Problema | Como verificar |
| --- | --- |
| Python não encontrado ou versão incompatível | Confira `py -3 --version` no Windows ou `python3 --version` nos demais sistemas. Instale Python 3.11 ou posterior e recrie o ambiente virtual. |
| `ModuleNotFoundError: tkinter` ou erro de Tcl/Tk | Instale o suporte a Tk da sua distribuição do Python ou do sistema. Tkinter não é uma dependência instalada pelo `pip` deste projeto. Consulte a [documentação do Tkinter](https://docs.python.org/3/library/tkinter.html). |
| A janela não abre em um servidor sem interface gráfica | Execute o aplicativo em uma sessão desktop com suporte a janelas. A interface Tkinter exige um ambiente gráfico. |
| Chave ausente ou configuração inválida | Confira `OPENAI_API_KEY` no `.env`, na raiz do projeto. Use uma chave real apenas no ambiente local e reinicie o aplicativo após alterar a configuração. |
| Erro de autenticação | Verifique se a chave está ativa e pertence à organização ou ao projeto pretendido. Não publique a chave para pedir ajuda. |
| Modelo indisponível ou sem permissão | Confira `OPENAI_MODEL`, a grafia do identificador e o acesso da organização ao modelo. Escolha uma opção compatível com a Responses API. |
| Limite de uso, quota ou cobrança | Confira o limite e o faturamento da API. Um limite temporário de requisições e a falta de créditos são situações distintas; observe a mensagem recebida. |
| Falha de conexão ou tempo de espera | Verifique a internet e eventuais restrições de rede. Tente novamente quando a conexão ou o serviço estiver disponível. |
| `No module named projectia`, `openai` ou `dotenv` | Execute novamente a instalação com o Python da `.venv` e use esse mesmo executável para iniciar o aplicativo. |

## Contribuições

Consulte o [guia de contribuição](CONTRIBUTING.md) para preparar alterações, executar as verificações e abrir um pull request.

## Referências

- [SDK oficial OpenAI para Python](https://github.com/openai/openai-python).
- [Referência da Responses API](https://developers.openai.com/api/reference/python/resources/responses/methods/create).
- [Biblioteca Tkinter do Python](https://docs.python.org/3/library/tkinter.html).

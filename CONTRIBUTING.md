# Contribuindo com o ProjectIA

O ProjectIA é um aplicativo didático em Python e Tkinter. As contribuições devem manter a configuração fora do código, a interface responsiva e a documentação coerente com o comportamento implementado.

## Preparar o ambiente

Siga a [instalação do README](README.md#instalação), utilizando Python 3.11 ou posterior. Para desenvolver, instale também as ferramentas de verificação:

**Windows:**

```powershell
.venv\Scripts\python -m pip install -e ".[dev]"
```

**Linux ou macOS:**

```sh
.venv/bin/python -m pip install -e ".[dev]"
```

Os testes automatizados não exigem uma chave de API real. Configure o `.env` apenas quando precisar executar manualmente a integração; envios reais podem gerar cobrança.

## Fazer uma alteração

1. Descreva o problema ou a melhoria pretendida. Para mudanças de escopo, explique primeiro o comportamento esperado em uma issue ou no pull request.
2. Atualize sua cópia local e crie uma branch com nome relacionado à alteração.
3. Implemente uma mudança com escopo claro, preservando a separação entre configuração, interface e serviço de API.
4. Acrescente ou ajuste testes quando o comportamento mudar. Utilize simulações para chamadas ao serviço externo.
5. Atualize o README e o `.env.example` se houver mudanças de instalação, configuração, uso ou dados enviados à API.
6. Execute as verificações e abra um pull request para revisão.

Exemplo de criação de branch a partir de uma cópia local atualizada:

```sh
git pull --ff-only
git switch -c melhoria/descricao-curta
```

Se não tiver permissão de escrita neste repositório, faça as alterações em um fork e abra o pull request a partir dele.

## Critérios de implementação

- Preserve as mensagens da interface em português.
- Evite operações de rede na thread responsável pela janela. As alterações de widgets Tkinter devem ocorrer na thread da interface.
- Trate erros de configuração e de serviço com mensagens úteis, sem expor credenciais.
- Mantenha o limite de entrada e a validação de perguntas vazias coerentes entre código, testes e documentação.
- Preserve o comportamento de perguntas independentes. Uma mudança para conversa com contexto ou armazenamento de histórico precisa explicitar o novo fluxo de dados e ter seus requisitos discutidos.
- Use as dependências declaradas no `pyproject.toml`. Explique a necessidade de uma dependência nova.
- Não adicione chamadas reais à API aos testes automatizados ou à integração contínua.

## Executar as verificações

**Windows:**

```powershell
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m ruff format --check .
```

**Linux ou macOS:**

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
```

Para mudanças na interface, abra o aplicativo e confira os estados afetados: entrada vazia, limite de caracteres, envio em andamento, resposta e falha. Informe no pull request quais estados foram verificados e em qual sistema operacional. Se algum cenário não puder ser executado, registre a limitação.

## Credenciais e arquivos locais

Não inclua no commit o arquivo `.env`, chaves de API, ambientes virtuais, logs com dados pessoais ou capturas de tela com credenciais. Mantenha somente valores demonstrativos no `.env.example`.

Antes de enviar alterações, confira os arquivos preparados para o commit:

```sh
git status
git diff --cached
```

Se uma chave real já tiver sido publicada, revogue-a no serviço e substitua-a. Apagar a linha em um commit posterior não remove a credencial do histórico do Git. Não copie a chave para uma issue ou um comentário ao relatar o incidente.

## Abrir um pull request

Apresente o problema resolvido, o comportamento resultante e as verificações executadas. Inclua instruções de reprodução quando houver um defeito específico. Para alterações visuais, uma captura da janela com dados fictícios pode ajudar a revisão.

Evite agrupar correções independentes no mesmo pull request. Responda às observações da revisão e atualize os testes ou a documentação quando o escopo final mudar.

# DevCodeArena

Plataforma Django para desafios de programação, avaliação de submissões e contato contextual entre empresas e desenvolvedores.

## Requisitos

- Python compatível com a versão de Django definida em requirements.txt.
- SQLite, configurado como banco padrão.
- Nenhuma dependência nova é necessária para esta fase.

## Executar localmente

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py check
python manage.py test
python manage.py runserver
```

Abra http://127.0.0.1:8000/ no navegador. Acesse o Django Admin em /admin/ depois de criar um superusuário com `python manage.py createsuperuser`.

## Fluxos nesta versão

- Cadastro/login para desenvolvedores (CPF) e empresas (CNPJ), com validação e armazenamento separados dos identificadores.
- Perfis profissionais editáveis com nome público, apresentação, competências, tecnologias e links de portfólio; CPF permanece obrigatório no cadastro e privado.
- Página inicial responsiva com uma arena 3D em CSS que representa desafios e talentos, movimento de ponteiro, animações pausadas fora da tela, suporte a movimento reduzido e sem renderização WebGL contínua.
- Catálogo de desafios publicados, ciclos semanais/mensais, filtros via GET e paginação.
- Rascunhos, publicação, edição, encerramento e gestão de desafios próprios por empresa.
- Inscrição única por desenvolvedor/desafio e envio do URL do repositório.
- Avaliação manual de 0 a 100 pela empresa dona do desafio.
- Ranking baseado na soma das notas avaliadas; notas pendentes não contam.
- Conversas persistidas, acessíveis somente aos participantes, criadas após seleção de um desenvolvedor com submissão avaliada.
- Alternância de tema claro/escuro herdada da interface existente e layouts responsivos.

## Decisões e limites

- A migration 0003_platform_features acrescenta os recursos sem apagar as tabelas de perfis nem os desafios existentes; a migration seguinte adiciona campos profissionais opcionais.
- CPF e CNPJ são dados privados e não são exibidos nas páginas públicas nem na listagem padrão do admin. Contas anteriores mantêm o CPF armazenado; novos cadastros empresariais usam CNPJ.
- A avaliação é manual e identificada: as empresas responsáveis veem o perfil profissional do participante e seus links durante a análise. Esta versão não oferece avaliação cega.
- A plataforma não intermedeia contratação ou pagamentos. O campo de recompensa registra o valor informado pela empresa; não representa pagamento garantido nem processado pela plataforma.
- O produto atual é focado em desafios individuais para demonstrar habilidades e aproximar empresas e desenvolvedores. Não há equipes, etapas ou gestão de eventos de hackathon, nem projetos freelance com propostas, contratos ou pagamentos.
- Esta versão não executa código enviado por usuários, não fornece isolamento de execução, não possui WebSockets nem integração externa de recrutamento.
- A classificação atual é uma soma simples e global das notas avaliadas. Não há histórico por período nem detecção de fraude.
- Antes de produção: defina `DJANGO_SECRET_KEY` com uma chave nova e privada, `DJANGO_DEBUG=False` e `DJANGO_ALLOWED_HOSTS=seu-dominio.com` no ambiente de execução. A aplicação recusa iniciar em modo de produção sem chave e hosts configurados. A chave que já esteve versionada deve ser considerada comprometida e rotacionada; não a reutilize. Configure HTTPS, backups, política de retenção de dados pessoais e revise a segurança. Não apague db.sqlite3 para aplicar migrations.

## Testes

Os testes automatizados cobrem listagem, inscrição única, bloqueio de papéis indevidos, propriedade de desafios, privacidade das conversas, persistência de mensagens e critérios do ranking. Execute `python manage.py test` no ambiente com dependências instaladas.

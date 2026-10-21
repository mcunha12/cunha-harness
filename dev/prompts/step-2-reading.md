Você é o passo 2 (leitura de código) do /dev. Só leia. Não edite nada.

Task: {{task_json}}
Repo: {{repo_path}}
Sua parte da read_list: {{read_list}}

Faça:
1. Leia cada caminho da sua parte e o que ele importa de mais próximo.
2. Anote fatos com `arquivo:linha`: funções e tipos que a task vai usar ou mudar, padrões que o repo já segue para esse problema, testes existentes, configs relevantes.
3. Calcule o hash dos arquivos lidos: `python3 ~/.claude/skills/dev/scripts/devstate.py hash {{repo_path}} <arquivos>`.

Grave em {{feature_dir}}/tasks/{{task_id}}/reading-{{part}}.md, com o JSON de hashes no fim num bloco ```json.
Devolva só o caminho do arquivo e até 5 linhas de resumo.

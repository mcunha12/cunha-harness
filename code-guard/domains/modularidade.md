# Domínio: modularidade

- [MOD] Sem ciclo de import. Se dois módulos precisam um do outro, extraia o que é comum. — origem: review-modularidade/ciclo
- [MOD] Import não tem side effect: conexão, listener e registro global nascem em função chamada pelo bootstrap. — origem: review-modularidade/side-effect-no-import
- [MOD] Autorização fica no serviço de domínio, nunca só na camada de agregação. — origem: review-modularidade/camada
- [MOD] Domínio não importa ORM, SDK de vendor ou HTTP client; use port e adapter. — origem: review-modularidade/DIP
- [MOD] Camada de agregação (BFF, gateway) não ganha regra de negócio que o serviço dono já tem. — origem: review-modularidade/camada
- [MOD] Chamada a serviço interno passa pela porta que o README define. — origem: review-modularidade/fronteira
- [MOD] Sem `forwardRef` novo entre módulos Nest; reorganize a dependência. — origem: review-modularidade/nestjs
- [MOD] Importe pelo ponto público de outra feature, nunca por deep import. Sem `export *` que fecha ciclo ou arrasta módulo pesado. — origem: review-modularidade/encapsulamento
- [MOD] Módulo estável não passa a depender de módulo instável. — origem: review-modularidade/acoplamento
- [MOD] Variante nova que exige mudar 6 ou mais arquivos pede um ponto de extensão antes. — origem: review-modularidade/shotgun-surgery

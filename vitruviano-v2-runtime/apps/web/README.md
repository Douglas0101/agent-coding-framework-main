# Web App

Aplicacao Next.js do MVP. Reune frontend clinico e portal do paciente no mesmo servico web.

## Estrutura

- `app/`: roteamento e layouts do Next.js
- `src/components/`: componentes compartilhados de interface
- `src/features/auth/`: login, MFA e sessao
- `src/features/worklist/`: worklist canonica de estudos
- `src/features/study-viewer/`: pagina de estudo, viewer DICOM e overlays
- `src/features/report-editor/`: draft, versionamento, assinatura e release flow
- `src/features/patient-portal/`: publicacoes patient-facing autenticadas
- `src/features/ops-dashboard/`: probes reais de operacao
- `src/lib/`: cliente de API, RBAC, validacao e utilitarios
- `tests/`: testes de interface e fluxos do frontend

## Limites importantes

- Sem dependencia de DICOMweb no MVP
- Sem fluxo assincrono de inferencia
- Sem link publico anonimo para paciente

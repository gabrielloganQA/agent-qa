Snapshot das metricas, um arquivo por dia: AAAA-MM-DD.json

  python3 test/scripts/qa_dashboard.py --snapshot

Isto E versionado, ao contrario do dashboard.html. Metrica sem serie temporal
nao e metrica: "conversao 62%" nao diz se melhorou. A auditoria semanal calcula
tudo na hora e nao guarda nada -- este diretorio e a memoria.

Rode uma vez por semana, na auditoria, ou a cada release. Diario e ruido.

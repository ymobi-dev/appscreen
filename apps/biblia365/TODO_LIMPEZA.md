### 🚨 Pendente: Limpeza Pós-Screenshots

1.  **[ ] Streak de 12 Dias (Home)**
    *   **Arquivo:** `composeApp/src/commonMain/kotlin/com/ymobidev/mydevotional/app/screen/home/model/HomeScreenModel.kt`
    *   **O que reverter:** Remover o valor fixo `val streakDeferred = async { 12 }` e a lógica de fallback no cache.
2.  **[ ] Salmo 91:1-16 (Versículo do Dia)**
    *   **Arquivo:** `composeApp/src/commonMain/kotlin/com/ymobidev/mydevotional/app/repository/CuratedVerseRepository.kt`
    *   **O que reverter:** Voltar com a lógica de `restoreCachedDailyVerseContent` e `getDailyVerse(date)` na função `getDailyVerseContent`.
3.  **[✅] Barra de Progresso Anual (Home)**
    *   **Status:** MANTER na produção conforme solicitado. ✨

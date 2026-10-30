export function createPersonalDataScope(initialUserId = null) {
  let userId = initialUserId;
  let generation = 0;

  return {
    setUserId(nextUserId) {
      if (nextUserId === userId) return false;
      userId = nextUserId;
      generation += 1;
      return true;
    },
    capture() {
      return { userId, generation };
    },
    isCurrent(snapshot) {
      return Boolean(
        snapshot
        && userId !== null
        && snapshot.userId === userId
        && snapshot.generation === generation,
      );
    },
    invalidate() {
      userId = null;
      generation += 1;
    },
  };
}

/** Clear every in-memory field that can contain or indicate user-owned data. */
export function resetPersonalDataState(setters, { initialProfile, emptyTotals }) {
  setters.setTodayLog({ meals: [] });
  setters.setDailyTotals({ ...emptyTotals });
  setters.setDailyLoading(false);
  setters.setDailyError('');
  setters.setMealActionError('');
  setters.setIsSavingMeal(false);
  setters.setPendingMealId(null);
  setters.setIsLoggingAnalysisMeal(false);
  setters.setUserProfile({ ...initialProfile, dietary_preferences: [], targets: null });
  setters.setProfileLoading(false);
  setters.setProfileLoaded(false);
  setters.setProfileError('');
  setters.setProfileActionError('');
  setters.setIsSavingProfile(false);
}

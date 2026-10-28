import { createContext, useContext, useState } from "react";

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [currentCandidate, setCurrentCandidateState] = useState(null);
  const [currentJD, setCurrentJD] = useState(null);

  const setCurrentCandidate = (cand) => {
    if (!cand) {
      setCurrentCandidateState(null);
      return;
    }
    const cid = cand.candidate_id || cand.id;
    setCurrentCandidateState({ ...cand, candidate_id: cid, id: cid });
  };

  return (
    <AppContext.Provider
      value={{
        currentCandidate,
        setCurrentCandidate,
        currentJD,
        setCurrentJD,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useAppContext() {
  const context = useContext(AppContext);

  if (!context) {
    throw new Error("useAppContext must be used inside AppProvider");
  }

  return context;
}

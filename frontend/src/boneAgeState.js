/**
 * Bone-age workspace state (M6 state ownership).
 *
 * The sixty-odd useState bindings behind the bone-age tab, plus the two refs and
 * the one effect that belong with them. Companion to `boneAgeHandlers.js`: that
 * module holds the workflow, this one holds what the workflow acts on.
 *
 * What this move is, and what it deliberately is not
 * --------------------------------------------------
 * M6 deferred relocating state ownership out of App, on the stated condition
 * that it follow "if it ever pays for itself". An audit of the sharing surface
 * is what decided the shape:
 *
 *   - 97 useState bindings in App, 156 names on the context.
 *   - 109 of those names are read by exactly ONE panel.
 *   - but every one of them is also read by App itself, or by the handler hook
 *     App owns -- boneMetrics feeds the Overview cards, resetAll clears them,
 *     the adult-height projection needs the parental heights.
 *
 * So moving ownership OUT of App would mean threading the same values straight
 * back in. The sharing surface cannot shrink without either a second provider
 * (which M6 weighed and rejected -- no render saving, a harder tree to read) or
 * inverting the data flow so panels report upward.
 *
 * What does pay for itself is grouping: this hook is still called during App's
 * render, so ownership is unchanged and every consumer keeps working, but the
 * declarations, their defaults and the comments explaining them now live with
 * their domain instead of in a 60-line run inside a 1,300-line component. The
 * module boundary enforces the grouping that a comment header only suggested.
 *
 * Returns one flat bag so App can destructure it exactly as it declared these
 * before -- no call site below changes, which is what keeps a move of this size
 * mechanical rather than risky.
 */
const { useState, useRef, useEffect } = React;

// Hard quality flags the clinician can declare; any one makes the AI estimate
// abstain. Constant rather than state -- it is the vocabulary, not a value.
const DECLARABLE_FLAGS = [
  ['FRACTURE', 'Fracture'], ['CAST_OR_HARDWARE', 'Cast / hardware'],
  ['WRONG_LATERALITY', 'Wrong side'], ['CLIPPED_DIGITS', 'Clipped anatomy'],
  ['SEVERE_DEFORMITY', 'Deformity'], ['FOREIGN_OBJECT', 'Foreign object'],
];

function useBoneAgeState() {
  const [boneAge, setBoneAge] = useState("");        // TW3 bone age (RUS-derived or manual)
  const [boneAgeSource, setBoneAgeSource] = useState("manual"); // manual | rus
  const [rusStages, setRusStages] = useState({});    // { boneCode: 'A'..'I' }
  const [carpalStages, setCarpalStages] = useState({}); // { carpalName: 'A'..'I' }
  const [tw3Config, setTw3Config] = useState(null);  // /api/bone-age/config
  const [rusResult, setRusResult] = useState(null);  // /api/bone-age/score
  const [letterResult, setLetterResult] = useState(null); // live /letters-score (RUS+carpal)
  const [boneReport, setBoneReport] = useState(null); // live /report (structured 20-bone)
  const [patientCode, setPatientCode] = useState(""); // assessment lifecycle
  const [approverName, setApproverName] = useState("");
  const [assessment, setAssessment] = useState(null); // saved lifecycle record
  const [lcMsg, setLcMsg] = useState(null);           // {type:'ok'|'err', text}
  const [lcBusy, setLcBusy] = useState(false);
  const [showAudit, setShowAudit] = useState(false);
  const [radiograph, setRadiograph] = useState(null); // attached film metadata
  const [coverage, setCoverage] = useState(null);     // /api/bone-age/coverage
  const [covBusy, setCovBusy] = useState(false);
  const [monitoring, setMonitoring] = useState(null); // /api/bone-age/monitoring
  const [monBusy, setMonBusy] = useState(false);
  const [localCohort, setLocalCohort] = useState(null); // /api/bone-age/local-cohort
  const [lcohBusy, setLcohBusy] = useState(false);
  const [adjItems, setAdjItems] = useState(null);     // /api/bone-age/adjudication (open)
  const [adjBusy, setAdjBusy] = useState(false);
  const [adjReviewer, setAdjReviewer] = useState(""); // the resolving clinician
  const [adjMsg, setAdjMsg] = useState(null);
  const [ltTables, setLtTables] = useState(null);     // licensed TW3 tables editor
  const [ltStatus, setLtStatus] = useState(null);
  const [ltSection, setLtSection] = useState('rus');  // rus | carpal | curves | ref
  const [ltSex, setLtSex] = useState('boys');
  const [ltMsg, setLtMsg] = useState(null);
  const [ltBusy, setLtBusy] = useState(false);
  const [boxes, setBoxes] = useState({});       // {bone_code:[x0,y0,x1,y1] in image px}
  const [locImg, setLocImg] = useState(null);   // {width,height}
  const [locBusy, setLocBusy] = useState(false);
  const [locMsg, setLocMsg] = useState(null);
  const [selBone, setSelBone] = useState(null);
  const locDrag = useRef(null);
  const locRef = useRef(null);
  const boxesRef = useRef({});          // always-current boxes (avoids stale closures)
  useEffect(() => { boxesRef.current = boxes; }, [boxes]);
  const [aiEstimate, setAiEstimate] = useState(null); // AI screening estimate
  const [estimateDomain, setEstimateDomain] = useState('unknown'); // quality gate for quick estimate
  const [declaredFlags, setDeclaredFlags] = useState([]); // clinician-declared image issues (S-BA-6 gate)
  const [lastFilm, setLastFilm] = useState(null);         // last attached film, to re-gate on flag toggle
  // Suggestion box — clinician's corrected bone age (self-improvement flywheel).
  const [fbAge, setFbAge] = useState('');
  const [fbMethod, setFbMethod] = useState('tw3-rus');
  const [fbConfidence, setFbConfidence] = useState('medium');
  const [fbRater, setFbRater] = useState('');
  const [fbNote, setFbNote] = useState('');
  const [fbMsg, setFbMsg] = useState(null);
  const [fbBusy, setFbBusy] = useState(false);
  const [aiBusy, setAiBusy] = useState(false);
  // Parental heights live here because the bone-age tab collects them, but the
  // GROWTH panel's adult-height projection reads them too -- one of the reasons
  // this state cannot simply move into the bone-age panel.
  const [fatherHeight, setFatherHeight] = useState("");
  const [motherHeight, setMotherHeight] = useState("");

  return {
    DECLARABLE_FLAGS,
    boneAge, setBoneAge, boneAgeSource, setBoneAgeSource,
    rusStages, setRusStages, carpalStages, setCarpalStages,
    tw3Config, setTw3Config, rusResult, setRusResult,
    letterResult, setLetterResult, boneReport, setBoneReport,
    patientCode, setPatientCode, approverName, setApproverName,
    assessment, setAssessment, lcMsg, setLcMsg, lcBusy, setLcBusy,
    showAudit, setShowAudit, radiograph, setRadiograph,
    coverage, setCoverage, covBusy, setCovBusy,
    monitoring, setMonitoring, monBusy, setMonBusy,
    localCohort, setLocalCohort, lcohBusy, setLcohBusy,
    adjItems, setAdjItems, adjBusy, setAdjBusy,
    adjReviewer, setAdjReviewer, adjMsg, setAdjMsg,
    ltTables, setLtTables, ltStatus, setLtStatus,
    ltSection, setLtSection, ltSex, setLtSex,
    ltMsg, setLtMsg, ltBusy, setLtBusy,
    boxes, setBoxes, locImg, setLocImg, locBusy, setLocBusy,
    locMsg, setLocMsg, selBone, setSelBone,
    locDrag, locRef, boxesRef,
    aiEstimate, setAiEstimate, estimateDomain, setEstimateDomain,
    declaredFlags, setDeclaredFlags, lastFilm, setLastFilm,
    fbAge, setFbAge, fbMethod, setFbMethod,
    fbConfidence, setFbConfidence, fbRater, setFbRater,
    fbNote, setFbNote, fbMsg, setFbMsg, fbBusy, setFbBusy,
    aiBusy, setAiBusy,
    fatherHeight, setFatherHeight, motherHeight, setMotherHeight,
  };
}

export { useBoneAgeState, DECLARABLE_FLAGS };

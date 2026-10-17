export function createRequestSequence() {
  let latestRequestId = 0;

  return {
    next() {
      latestRequestId += 1;
      return latestRequestId;
    },
    isCurrent(requestId) {
      return requestId === latestRequestId;
    },
  };
}

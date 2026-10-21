export function Notes() {
  return (
    <div className="film-notes research-notes research-width" id="study-notes">
      <details>
        <summary>
          Published results <span aria-hidden="true">+</span>
        </summary>
        <div className="notes-columns">
          <div>
            <h3>Reported performance</h3>
            <p>
              The Yantai results come from LaDe, Table 4. M2G4RTP has the lowest mean absolute error (MAE)
              among the four methods shown. These are published results, not our reruns.
            </p>
            <p>The audit describes the inspected code, not every historical paper configuration.</p>
          </div>
          <div>
            <h3>Comparison limits</h3>
            <p>
              Published results, checkpoint rescores and the matched rerun use different inputs and
              populations. Do not compare the paper’s 17.21 minutes directly with Hermes’s 58.64 minutes.
            </p>
          </div>
        </div>
        <a
          className="research-source"
          href="https://arxiv.org/html/2306.10675v3#S4.T4"
          target="_blank"
          rel="noopener noreferrer"
        >
          LaDe, Table 4 ↗
        </a>
      </details>
      <details>
        <summary>
          Input and scoring audit <span aria-hidden="true">+</span>
        </summary>
        <div className="notes-columns">
          <div>
            <h3>Future information</h3>
            <p>
              The inspected pipeline keeps pending parcels only if they finish within the next two hours. It
              also uses future delivery order and full-period statistics. This information would not be
              available at prediction time.
            </p>
            <p>The parcel examples are fictional.</p>
            <a
              className="research-source"
              href="https://github.com/wenhaomin/LaDe/blob/9e5155a5e03b0e752749f726914f73bf08d62666/time_prediction/data/dataset_delivery.py#L141-L164"
              target="_blank"
              rel="noopener noreferrer"
            >
              Input filter ↗
            </a>
          </div>
          <div>
            <h3>Parcel identity</h3>
            <p>
              The inspected M2G4RTP evaluator matches times by route position, not parcel identity. Rescoring
              local checkpoints by parcel increases MAE:
            </p>
            <table className="notes-table">
              <thead>
                <tr>
                  <th scope="col">Pipeline / predictions</th>
                  <th scope="col">Position MAE</th>
                  <th scope="col">Parcel MAE</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <th scope="row">Original / 131,454</th>
                  <td>12.47</td>
                  <td>22.19</td>
                </tr>
                <tr>
                  <th scope="row">Partly cleaned / 200,534</th>
                  <td>12.09</td>
                  <td>23.27</td>
                </tr>
              </tbody>
            </table>
            <p>
              MAE is in minutes. Compare scoring rules within each row, not performance across populations.
              Neither row is the matched rerun.
            </p>
            <p>
              Partial cleanup restricts statistics to training data, removes true-order area features and
              retains busy days. Both versions still use future filtering and task windows.
            </p>
            <a
              className="research-source"
              href="https://github.com/wenhaomin/LaDe/blob/9e5155a5e03b0e752749f726914f73bf08d62666/time_prediction/algorithm/m2g4rtp_delivery/train.py"
              target="_blank"
              rel="noopener noreferrer"
            >
              Evaluator ↗
            </a>
          </div>
        </div>
        <a
          className="research-source"
          href="/assets/frontier-rescoring.json"
          download="hermes-frontier-rescoring.json"
        >
          Rescoring results ↓
        </a>
      </details>
      <details>
        <summary>
          Matched rerun and limitations <span aria-hidden="true">+</span>
        </summary>
        <div className="notes-columns">
          <div>
            <h3>Matched comparison</h3>
            <p>
              On 149,263 matched Yantai parcel-checkpoint predictions, M2G4RTP records 77.11 minutes MAE and
              Hermes 58.64: a 24% reduction in error for pending parcels.
            </p>
            <p>
              Training precedes September 1; model selection uses September 1–15; evaluation uses September
              16–30. M2G4RTP epoch 12 was selected on stopping performance.
            </p>
            <p>
              This is a local adaptation, not an exact paper reproduction. Saved metrics and training history
              are available; the full matched-run script is not archived.
            </p>
          </div>
          <div>
            <h3>Limits</h3>
            <p>
              September informed development. Queries repeat across parcels and courier-days; 149,263 is not a
              unique-parcel count. No repeat-run uncertainty or untouched October evaluation is available.
            </p>
            <p>
              Recorded completion is not verified receipt. Data availability is approximate, and pending
              records may be incomplete.
            </p>
            <p>
              The result is an average improvement, not a guarantee for every parcel or evidence of deployment
              readiness. Stock photographs are illustrative.
            </p>
          </div>
        </div>
        <div className="evidence-links">
          <a
            className="research-source"
            href="/assets/frontier-comparison.json"
            download="hermes-frontier-comparison.json"
          >
            Matched metrics and training history ↓
          </a>
        </div>
        <p className="rights-note">
          Dataset card: Apache-2.0. Paper: CC BY-NC 4.0. Confirm applicable terms before redistribution. No
          raw records or trained models are included. AI assisted coding and presentation; predictive models
          ran locally.
        </p>
      </details>
    </div>
  );
}

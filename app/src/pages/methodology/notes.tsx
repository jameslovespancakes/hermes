export function Notes() {
  return (
    <section className="method-notes wrap" id="study-notes" aria-label="Methodology notes and sources">
      <details>
        <summary>
          Data and evaluation <span aria-hidden="true">+</span>
        </summary>
        <div className="method-note-columns">
          <div>
            <h3>Study design</h3>
            <p>
              LaDe-D delivery records from Yantai are used to predict remaining time for pending parcels at
              each recorded delivery checkpoint.
            </p>
            <p>
              Training uses events and outcomes before September 1. September 1–15 selects the model;
              September 16–30 evaluates it.
            </p>
          </div>
          <div>
            <h3>Evaluation limits</h3>
            <p>
              The evaluation includes 155,296 queries across 14,234 parcels. September informed development;
              October was not tested. Repeated queries are dependent, and no repeat-run uncertainty is
              available.
            </p>
            <p>
              Event times approximate data availability. Actual ingestion delays are unknown; recorded
              completion is not independently verified receipt.
            </p>
          </div>
        </div>
      </details>
      <details>
        <summary>
          Models <span aria-hidden="true">+</span>
        </summary>
        <div className="method-note-columns">
          <div>
            <h3>Order and ETA</h3>
            <p>
              A LightGBM model predicts stop order. Its output feeds the standard ETA model alongside current
              context and historical patterns. A separate delay-aware ETA model handles stale feeds.
            </p>
            <p>
              Training uses out-of-fold order predictions and excludes the current courier-day from transition
              statistics. Model weights stay fixed during replay.
            </p>
          </div>
          <div>
            <h3>Input limits</h3>
            <p>
              Pending work may be incomplete. The last completed stop approximates courier location;
              straight-line distance is not road travel time.
            </p>
            <p>
              The line fan illustrates boosting, not fitted trees or individual predictions. Stop-order
              prediction is not road-route optimization.
            </p>
          </div>
        </div>
      </details>
      <details>
        <summary>
          Cleaning and monitoring <span aria-hidden="true">+</span>
        </summary>
        <div className="method-note-columns">
          <div>
            <h3>Record cleaning</h3>
            <p>
              The loader rejects missing IDs, all copies of repeated IDs, invalid timestamps and negative
              durations. Zero-duration and long deliveries are kept.
            </p>
            <p>
              The guard removes re-sent copies, repairs large GPS offsets using historical area medians, and
              excludes bulk-scanned courier-days from training. Repairs are estimates, not verified locations.
            </p>
          </div>
          <div>
            <h3>Prediction and monitoring</h3>
            <p>
              During prediction, bulk scans are retained and flagged. Feed age or upload lag can select a
              delay-aware ETA model. Data-contract and drift checks report input changes; a sampled comparison
              gates model replacement.
            </p>
            <p>
              In a separate simulation, the full set of controls reduced MAE under combined faults from 84.0
              to 66.9 minutes. This does not isolate cleaning or establish live reliability. Missing events
              remain unknown.
            </p>
          </div>
        </div>
        <div className="evidence-links">
          <a
            className="research-source"
            href="/assets/current-data-quality.json"
            download="hermes-data-quality-experiment.json"
          >
            Simulated data-quality results ↓
          </a>
        </div>
      </details>
      <details>
        <summary>
          Results and sources <span aria-hidden="true">+</span>
        </summary>
        <div className="method-note-columns">
          <div>
            <h3>Comparable results</h3>
            <p>
              The saved matched rerun scores M2G4RTP at 77.11 minutes MAE and Hermes at 58.64 on the same
              149,263 predictions. Only M2G4RTP has this matched comparison.
            </p>
            <p>
              Published LaDe scores (Yantai MAE: LightGBM 23.32, FDNET 22.41, RankETPA 21.36, M2G4RTP 17.21)
              use different inputs, populations and evaluation, so they cannot be ranked against Hermes.
            </p>
          </div>
          <div>
            <h3>Current pipeline</h3>
            <p>
              The current cleaning-enabled bundle scores 58.48 minutes MAE on 155,296 development queries.
              This is a separate run, not a replacement for the matched score.
            </p>
            <p>
              For queries with 3–24 hours remaining, its MAE is 107.06 minutes. These are development results,
              not deployment evidence. Diagrams and photographs are illustrative.
            </p>
          </div>
        </div>
        <div className="evidence-links">
          <a
            className="research-source"
            href="/assets/current-model-metrics.json"
            download="hermes-current-model-metrics.json"
          >
            Current model metrics ↓
          </a>
          <a
            className="research-source"
            href="/assets/frontier-comparison.json"
            download="hermes-frontier-comparison.json"
          >
            Matched rerun ↓
          </a>
          <a
            className="research-source"
            href="https://arxiv.org/html/2306.10675v3#S4.T4"
            target="_blank"
            rel="noopener noreferrer"
          >
            LaDe, Table 4 ↗
          </a>
          <a
            className="research-source"
            href="https://huggingface.co/datasets/Cainiao-AI/LaDe/tree/be2cec02775cafc8d52230303f32134382bcc50b"
            target="_blank"
            rel="noopener noreferrer"
          >
            Dataset revision ↗
          </a>
        </div>
        <p className="rights-note">
          Dataset card: Apache-2.0. Paper: CC BY-NC 4.0. Confirm applicable terms before redistribution. No
          raw records or trained models are included. AI assisted coding and presentation; predictive models
          ran locally.
        </p>
      </details>
    </section>
  );
}

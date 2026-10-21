import { Nav } from '../../nav';
import { Defs } from './defs';
import { Parcel } from './parcel';
import { Unpack } from './unpack';
import { Dataset } from './dataset';
import { Models } from './models';
import { Hygiene } from './hygiene';
import { Results } from './results';
import { Notes } from './notes';

export function Page() {
  return (
    <>
      <Defs />
      <a className="skip" href="#main">
        Skip to methodology
      </a>
      <Nav page="methodology" />
      <main id="main">
        <div className="method-journey" id="method-journey">
          <div className="method-background" aria-hidden="true" />
          <Parcel />
          <Unpack />
          <Dataset />
          <Hygiene />
          <Models />
          <Results />
        </div>
        <Notes />
      </main>
    </>
  );
}

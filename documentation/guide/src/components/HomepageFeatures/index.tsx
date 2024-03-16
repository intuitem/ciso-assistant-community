import clsx from 'clsx';
import Heading from '@theme/Heading';
import styles from './styles.module.css';

type FeatureItem = {
  title: string;
  Svg: React.ComponentType<React.ComponentProps<'svg'>>;
  description: JSX.Element;
};

const FeatureList: FeatureItem[] = [
  {
    title: 'Easy to Use',
    Svg: require('@site/static/img/easy_to_use.svg').default,
    description: (
      <>
        Simplify the process by organizing, interpreting and prioritizing data.
        This makes it possible to identify potential threats quickly, and to react swiftly to mitigate risks.
      </>
    ),
  },
  {
    title: 'Focus on What Matters',
    Svg: require('@site/static/img/focus.svg').default,
    description: (
      <>
        The main challenge is to find an efficient way of managing this deluge of information without compromising the sensitivity or confidentiality of your data.
      </>
    ),
  },
  {
    title: 'End-to-End',
    Svg: require('@site/static/img/end_to_end.svg').default,
    description: (
      <>
        Aim to be a one stop shop for cyber security management and cover the layers of GRC (Governance, Risk and Compliance).
      </>
    ),
  },
];

function Feature({title, Svg, description}: FeatureItem) {
  return (
    <div className={clsx('col col--4 flex flex-col')}>
      <div className="flex justify-center">
        <Svg className={styles.featureSvg} role="img" />
      </div>
      <div className="text--center padding-horiz--md">
        <Heading as="h3" className="font-bold">{title}</Heading>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures(): JSX.Element {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}

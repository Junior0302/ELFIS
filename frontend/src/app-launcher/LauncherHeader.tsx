import { ProductMark } from './ProductMark'

import { getProductById } from '../design-system'

import { cx } from '../design-system/components/cx'

import { Link } from 'react-router-dom'



export type LauncherHeaderProps = {

  titleId: string

  descriptionId: string

  embedded?: boolean

  onNavigateAway?: () => void

}



const SUBTITLE =

  'Accédez à tous les métiers de votre entreprise depuis un seul espace.'



export function LauncherHeader({

  titleId,

  descriptionId,

  embedded = false,

  onNavigateAway,

}: LauncherHeaderProps) {

  const platform = getProductById('elfis-core')



  return (

    <header className={cx('launcher-header', embedded && 'launcher-header--embedded')}>

      <div className="launcher-header__brand">

        <ProductMark product={platform} size="md" />

        <div>

          <p className="launcher-header__eyebrow">ELFIS</p>

          <p id={titleId} className="launcher-header__title">

            Espaces ELFIS

          </p>

        </div>

        <Link

          className="launcher-header__home"

          to="/home"

          onClick={onNavigateAway}

        >

          Accueil ELFIS

        </Link>

      </div>

      {!embedded ? (

        <p id={descriptionId} className="launcher-header__subtitle">

          {SUBTITLE}

        </p>

      ) : (

        <p id={descriptionId} className="visually-hidden">

          {SUBTITLE}

        </p>

      )}

    </header>

  )

}



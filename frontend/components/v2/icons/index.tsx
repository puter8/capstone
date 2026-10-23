/**
 * Pally v2 icon set, exported from Figma (Pally v2/Icon/* and the reused Pally v1/Icon/*).
 * Lucide-style 24px line icons; strokes are bound to currentColor so the text color recolors them.
 * Generated from the Figma SVG exports; edit the design, not this file, when an icon changes.
 */
import type { SVGProps } from "react";

export type IconProps = Omit<SVGProps<SVGSVGElement>, "width" | "height"> & {
  /** Rendered box in px. Icons are drawn on a 24px grid. */
  size?: number;
};

function IconBase({ size = 24, children, ...props }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      {children}
    </svg>
  );
}

export function IconChevronLeft(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M15 18L9 12L15 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </IconBase>
  );
}

export function IconChevronRight(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M9 18L15 12L9 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </IconBase>
  );
}

export function IconChevronDown(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M6 9L12 15L18 9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </IconBase>
  );
}

export function IconArrowRight(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M5 12H19" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M12 5L19 12L12 19" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </IconBase>
  );
}

export function IconX(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M6 6L18 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </IconBase>
  );
}

export function IconPencil(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M21.174 6.81189C21.7027 6.28332 21.9998 5.56636 21.9999 4.81875C22 4.07113 21.7031 3.3541 21.1745 2.82539C20.6459 2.29668 19.929 1.99961 19.1813 1.99951C18.4337 1.99942 17.7167 2.29632 17.188 2.82489L3.842 16.1739C3.60981 16.4054 3.43811 16.6904 3.342 17.0039L2.021 21.3559C1.99515 21.4424 1.9932 21.5342 2.01535 21.6217C2.03749 21.7092 2.08292 21.7891 2.14679 21.8529C2.21067 21.9167 2.29062 21.962 2.37815 21.984C2.46569 22.006 2.55755 22.0039 2.644 21.9779L6.997 20.6579C7.31017 20.5626 7.59517 20.392 7.827 20.1609L21.174 6.81189Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M15 5L19 9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </IconBase>
  );
}

export function IconVolume(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M11 4.70203C10.9998 4.56274 10.9583 4.42663 10.8809 4.31088C10.8034 4.19514 10.6934 4.10493 10.5647 4.05166C10.436 3.99838 10.2944 3.98442 10.1577 4.01154C10.0211 4.03866 9.89559 4.10564 9.797 4.20403L6.413 7.58703C6.2824 7.7184 6.12703 7.82256 5.95589 7.89345C5.78475 7.96435 5.60124 8.00057 5.416 8.00003H3C2.73478 8.00003 2.48043 8.10539 2.29289 8.29292C2.10536 8.48046 2 8.73481 2 9.00003V15C2 15.2652 2.10536 15.5196 2.29289 15.7071C2.48043 15.8947 2.73478 16 3 16H5.416C5.60124 15.9995 5.78475 16.0357 5.95589 16.1066C6.12703 16.1775 6.2824 16.2817 6.413 16.413L9.796 19.797C9.8946 19.8958 10.0203 19.9631 10.1572 19.9904C10.2941 20.0177 10.436 20.0037 10.5649 19.9503C10.6939 19.8968 10.804 19.8063 10.8815 19.6902C10.959 19.5741 11.0002 19.4376 11 19.298V4.70203Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M16 9C16.6491 9.86548 17 10.9181 17 12C17 13.0819 16.6491 14.1345 16 15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M19.364 18.364C20.1998 17.5283 20.8627 16.5361 21.315 15.4442C21.7673 14.3522 22.0001 13.1819 22.0001 12C22.0001 10.8181 21.7673 9.64775 21.315 8.55581C20.8627 7.46387 20.1998 6.47172 19.364 5.63599" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </IconBase>
  );
}

export function IconTranslate(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M5 8L11 14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M4 14L10 8L12 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M2 5H14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M7 2H8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M22 22L17 12L12 22" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M14 18H20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </IconBase>
  );
}

export function IconTrash(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M3 6H21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M19 6V20C19 21 18 22 17 22H7C6 22 5 21 5 20V6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M8 6V4C8 3 9 2 10 2H14C15 2 16 3 16 4V6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M10 11V17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M14 11V17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </IconBase>
  );
}

export function IconLogOut(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M16 17L21 12L16 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M21 12H9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M9 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V5C3 4.46957 3.21071 3.96086 3.58579 3.58579C3.96086 3.21071 4.46957 3 5 3H9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </IconBase>
  );
}

export function IconSparkles(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M9.937 15.5C9.84772 15.1539 9.66734 14.8381 9.41462 14.5854C9.1619 14.3327 8.84607 14.1523 8.5 14.063L2.365 12.481C2.26033 12.4513 2.16821 12.3883 2.10261 12.3014C2.03702 12.2146 2.00153 12.1088 2.00153 12C2.00153 11.8912 2.03702 11.7854 2.10261 11.6986C2.16821 11.6118 2.26033 11.5487 2.365 11.519L8.5 9.93601C8.84595 9.84681 9.16169 9.66658 9.4144 9.41404C9.66711 9.16151 9.84757 8.84589 9.937 8.50001L11.519 2.36501C11.5484 2.25992 11.6114 2.16735 11.6983 2.1014C11.7853 2.03545 11.8914 1.99976 12.0005 1.99976C12.1096 1.99976 12.2157 2.03545 12.3027 2.1014C12.3896 2.16735 12.4526 2.25992 12.482 2.36501L14.063 8.50001C14.1523 8.84608 14.3327 9.1619 14.5854 9.41462C14.8381 9.66734 15.1539 9.84773 15.5 9.93701L21.635 11.518C21.7405 11.5471 21.8335 11.61 21.8998 11.6971C21.9661 11.7841 22.0021 11.8906 22.0021 12C22.0021 12.1094 21.9661 12.2159 21.8998 12.3029C21.8335 12.39 21.7405 12.4529 21.635 12.482L15.5 14.063C15.1539 14.1523 14.8381 14.3327 14.5854 14.5854C14.3327 14.8381 14.1523 15.1539 14.063 15.5L12.481 21.635C12.4516 21.7401 12.3886 21.8327 12.3017 21.8986C12.2147 21.9646 12.1086 22.0003 11.9995 22.0003C11.8904 22.0003 11.7843 21.9646 11.6973 21.8986C11.6104 21.8327 11.5474 21.7401 11.518 21.635L9.937 15.5Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </IconBase>
  );
}

export function IconFlame(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M8.5 14.5C9.16304 14.5 9.79893 14.2366 10.2678 13.7678C10.7366 13.2989 11 12.663 11 12C11 10.62 10.5 10 10 9C8.928 6.857 9.776 4.946 12 3C12.5 5.5 14 7.9 16 9.5C18 11.1 19 13 19 15C19 15.9193 18.8189 16.8295 18.4672 17.6788C18.1154 18.5281 17.5998 19.2997 16.9497 19.9497C16.2997 20.5998 15.5281 21.1154 14.6788 21.4672C13.8295 21.8189 12.9193 22 12 22C11.0807 22 10.1705 21.8189 9.32122 21.4672C8.47194 21.1154 7.70026 20.5998 7.05025 19.9497C6.40024 19.2997 5.88463 18.5281 5.53284 17.6788C5.18106 16.8295 5 15.9193 5 15C5 13.847 5.433 12.706 6 12C6 12.663 6.26339 13.2989 6.73223 13.7678C7.20107 14.2366 7.83696 14.5 8.5 14.5Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </IconBase>
  );
}

export function IconGraduation(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M21.42 10.9221C21.599 10.8431 21.7509 10.7134 21.8569 10.5489C21.9629 10.3845 22.0183 10.1925 22.0163 9.99685C22.0143 9.8012 21.9549 9.61044 21.8455 9.4482C21.7362 9.28596 21.5816 9.15937 21.401 9.08411L12.83 5.18011C12.5694 5.06126 12.2864 4.99976 12 4.99976C11.7136 4.99976 11.4306 5.06126 11.17 5.18011L2.6 9.08011C2.42196 9.15809 2.27051 9.28625 2.16416 9.44893C2.05781 9.61161 2.00117 9.80176 2.00117 9.99611C2.00117 10.1905 2.05781 10.3806 2.16416 10.5433C2.27051 10.706 2.42196 10.8341 2.6 10.9121L11.17 14.8201C11.4306 14.939 11.7136 15.0005 12 15.0005C12.2864 15.0005 12.5694 14.939 12.83 14.8201L21.42 10.9221Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M22 10V16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M6 12.5V16C6 16.7956 6.63214 17.5587 7.75736 18.1213C8.88258 18.6839 10.4087 19 12 19C13.5913 19 15.1174 18.6839 16.2426 18.1213C17.3679 17.5587 18 16.7956 18 16V12.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </IconBase>
  );
}

export function IconCard(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M20 5H4C2.89543 5 2 5.89543 2 7V17C2 18.1046 2.89543 19 4 19H20C21.1046 19 22 18.1046 22 17V7C22 5.89543 21.1046 5 20 5Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M2 10H22" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </IconBase>
  );
}

export function IconTranscript(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M21 15C21 15.5304 20.7893 16.0391 20.4142 16.4142C20.0391 16.7893 19.5304 17 19 17H7L3 21V5C3 4.46957 3.21071 3.96086 3.58579 3.58579C3.96086 3.21071 4.46957 3 5 3H19C19.5304 3 20.0391 3.21071 20.4142 3.58579C20.7893 3.96086 21 4.46957 21 5V15Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M13 8H7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M17 12H7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </IconBase>
  );
}

export function IconClock(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M12 6V12L16 14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </IconBase>
  );
}

export function IconAlert(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M12 8V12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M12 16H12.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </IconBase>
  );
}

export function IconMicOff(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M2 2L22 22" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M18.89 13.23C18.9622 12.824 18.999 12.4124 19 12V10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M5.00001 10V12C4.97966 13.3992 5.37913 14.7723 6.14684 15.9422C6.91456 17.1121 8.01529 18.0251 9.30696 18.5633C10.5986 19.1015 12.022 19.2402 13.3933 18.9616C14.7645 18.6829 16.0208 17.9997 17 17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M15 9.33999V4.99999C14.9959 4.32636 14.7653 3.6737 14.3452 3.14711C13.9251 2.62053 13.3399 2.25066 12.684 2.09708C12.0281 1.94349 11.3396 2.01514 10.7294 2.30046C10.1192 2.58579 9.62271 3.06819 9.32001 3.66999" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M9 9V12C9.00052 12.593 9.17675 13.1725 9.50643 13.6653C9.83611 14.1582 10.3045 14.5423 10.8523 14.7691C11.4002 14.996 12.0029 15.0554 12.5845 14.9399C13.1661 14.8243 13.7005 14.539 14.12 14.12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M12 19V22" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </IconBase>
  );
}

export function IconWifiOff(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M12 20H12.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M8.5 16.429C9.43464 15.5129 10.6912 14.9998 12 14.9998C13.3088 14.9998 14.5654 15.5129 15.5 16.429" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M5 12.8589C6.41803 11.4689 8.21781 10.5324 10.17 10.1689" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M19 12.8589C18.3979 12.2687 17.7235 11.757 16.993 11.3359" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M2 8.82C3.2366 7.71408 4.64809 6.82095 6.177 6.177" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M22 8.81991C20.4747 7.45573 18.6865 6.41806 16.7452 5.77074C14.8039 5.12343 12.7508 4.88016 10.712 5.05591" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M2 2L22 22" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </IconBase>
  );
}

export function IconReceipt(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M4 2V22L6 21L8 22L10 21L12 22L14 21L16 22L18 21L20 22V2L18 3L16 2L14 3L12 2L10 3L8 2L6 3L4 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M16 8H10C9.46957 8 8.96086 8.21071 8.58579 8.58579C8.21071 8.96086 8 9.46957 8 10C8 10.5304 8.21071 11.0391 8.58579 11.4142C8.96086 11.7893 9.46957 12 10 12H14C14.5304 12 15.0391 12.2107 15.4142 12.5858C15.7893 12.9609 16 13.4696 16 14C16 14.5304 15.7893 15.0391 15.4142 15.4142C15.0391 15.7893 14.5304 16 14 16H8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M12 17.5V6.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </IconBase>
  );
}

export function IconMic(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M12 2C11.2044 2 10.4413 2.31607 9.87868 2.87868C9.31607 3.44129 9 4.20435 9 5V12C9 12.7956 9.31607 13.5587 9.87868 14.1213C10.4413 14.6839 11.2044 15 12 15C12.7956 15 13.5587 14.6839 14.1213 14.1213C14.6839 13.5587 15 12.7956 15 12V5C15 4.20435 14.6839 3.44129 14.1213 2.87868C13.5587 2.31607 12.7956 2 12 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M19 10V12C19 13.8565 18.2625 15.637 16.9497 16.9497C15.637 18.2625 13.8565 19 12 19C10.1435 19 8.36301 18.2625 7.05025 16.9497C5.7375 15.637 5 13.8565 5 12V10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M12 19V22" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </IconBase>
  );
}

export function IconWaveform(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M2 10V13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M6 6V17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M10 3V21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M14 8V15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M18 5V18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M22 10V13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </IconBase>
  );
}

export function IconRotateCcw(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M3 12C3 13.78 3.52784 15.5201 4.51677 17.0001C5.50571 18.4802 6.91131 19.6337 8.55585 20.3149C10.2004 20.9961 12.01 21.1743 13.7558 20.8271C15.5016 20.4798 17.1053 19.6226 18.364 18.364C19.6226 17.1053 20.4798 15.5016 20.8271 13.7558C21.1743 12.01 20.9961 10.2004 20.3149 8.55585C19.6337 6.91131 18.4802 5.50571 17.0001 4.51677C15.5201 3.52784 13.78 3 12 3C9.48395 3.00947 7.06897 3.99122 5.26 5.74L3 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M3 3V8H8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </IconBase>
  );
}

export function IconSkipForward(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M5 4L15 12L5 20V4Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M19 5V19" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </IconBase>
  );
}

export function IconHome(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M3 10L12 3L21 10V19C21 19.5304 20.7893 20.0391 20.4142 20.4142C20.0391 20.7893 19.5304 21 19 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V10Z" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M9 21V13H15V21" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
    </IconBase>
  );
}

export function IconBook(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M18 3H7C5.89543 3 5 3.89543 5 5V19C5 20.1046 5.89543 21 7 21H18C19.1046 21 20 20.1046 20 19V5C20 3.89543 19.1046 3 18 3Z" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M5 17H20M9 9L11 11L15 7" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
    </IconBase>
  );
}

export function IconTrophy(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M12 14C13.0609 14 14.0783 13.5786 14.8284 12.8284C15.5786 12.0783 16 11.0609 16 10V3H8V10C8 11.0609 8.42143 12.0783 9.17157 12.8284C9.92172 13.5786 10.9391 14 12 14ZM12 14V19M8 5H4V8C4 9.06087 4.42143 10.0783 5.17157 10.8284C5.92172 11.5786 6.93913 12 8 12M16 5H20V8C20 9.06087 19.5786 10.0783 18.8284 10.8284C18.0783 11.5786 17.0609 12 16 12M8 21H16" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
    </IconBase>
  );
}

export function IconProfile(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M12 21C16.9706 21 21 16.9706 21 12C21 7.02944 16.9706 3 12 3C7.02944 3 3 7.02944 3 12C3 16.9706 7.02944 21 12 21Z" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M12 12C13.6569 12 15 10.6569 15 9C15 7.34315 13.6569 6 12 6C10.3431 6 9 7.34315 9 9C9 10.6569 10.3431 12 12 12Z" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M5.5 18C6.01936 16.7006 6.91623 15.5868 8.07486 14.8021C9.23349 14.0175 10.6007 13.5981 12 13.5981C13.3993 13.5981 14.7665 14.0175 15.9251 14.8021C17.0838 15.5868 17.9806 16.7006 18.5 18" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
    </IconBase>
  );
}

export function IconSpinner(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M11.9999 3.00001C13.9525 2.9976 15.853 3.6303 17.4145 4.80265C18.9761 5.97501 20.114 7.62341 20.6566 9.49916C21.1991 11.3749 21.117 13.3762 20.4224 15.2012C19.7279 17.0261 18.4587 18.5757 16.8063 19.6161C15.1539 20.6565 13.208 21.1313 11.2621 20.9688C9.31625 20.8063 7.476 20.0154 6.01903 18.7154C4.56205 17.4154 3.5674 15.6768 3.18514 13.7619C2.80288 11.847 3.05374 9.8598 3.89989 8.10001" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
    </IconBase>
  );
}

export function IconStop(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M16 5H8C6.34315 5 5 6.34315 5 8V16C5 17.6569 6.34315 19 8 19H16C17.6569 19 19 17.6569 19 16V8C19 6.34315 17.6569 5 16 5Z" fill="currentColor"/>
    </IconBase>
  );
}

export function IconRetry(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M3 10C3.46183 8.03558 4.57046 6.28335 6.14786 5.02474C7.72525 3.76612 9.67986 3.07415 11.6978 3.05995C13.7157 3.04574 15.6799 3.71014 17.2749 4.94643C18.8698 6.18272 20.003 7.91917 20.4924 9.8769C20.9819 11.8346 20.7991 13.9001 19.9736 15.7415C19.1481 17.5829 17.7277 19.0934 15.9404 20.0305C14.1532 20.9676 12.1029 21.2769 10.1188 20.9086C8.13472 20.5404 6.33194 19.516 5 18M9 10H3V4.00001" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
    </IconBase>
  );
}

export function IconCheck(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M5 12L9.8 16.8L19.5 6.75" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
    </IconBase>
  );
}

export function IconInfo(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M12 21C16.9706 21 21 16.9706 21 12C21 7.02944 16.9706 3 12 3C7.02944 3 3 7.02944 3 12C3 16.9706 7.02944 21 12 21Z" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M12 11V17M12 7V7.75" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
    </IconBase>
  );
}

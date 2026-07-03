// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
//
// Ankimatter Observatory — the iOS design system. Mirrors the desktop tokens in
// qt/aqt/data/web/css/pgre.scss so the two apps read as one product (see
// speedrun/UI_OBSERVATORY.md). A calm cosmic-dark instrument: bright cyan/violet
// and motion are reserved for the focal element; everything else is hairlines and
// dim text. All decoration is procedural (Canvas/SwiftUI shapes) — no sprites.

import SwiftUI

// MARK: - Color hex helper

extension Color {
    /// 0xRRGGBB literal, optional alpha.
    init(hex: UInt32, alpha: Double = 1) {
        self.init(
            .sRGB,
            red: Double((hex >> 16) & 0xFF) / 255,
            green: Double((hex >> 8) & 0xFF) / 255,
            blue: Double(hex & 0xFF) / 255,
            opacity: alpha)
    }
}

// MARK: - Palette (fixed dark; the app is Observatory-dark throughout)

enum Palette {
    static let space = Color(hex: 0x07080D)
    static let space2 = Color(hex: 0x0C1020)
    static let panel = Color(hex: 0x121520, alpha: 0.72)
    static let panel2 = Color(hex: 0x181C2A, alpha: 0.94)
    static let line = Color(hex: 0x96AADC, alpha: 0.16)
    static let lineStrong = Color(hex: 0x96AADC, alpha: 0.34)

    static let text = Color(hex: 0xEAF0FF)
    static let textDim = Color(hex: 0xEAF0FF, alpha: 0.62)
    static let textFaint = Color(hex: 0xEAF0FF, alpha: 0.36)

    static let accent = Color(hex: 0x4CE0FF) // electric cyan — focus only
    static let accent2 = Color(hex: 0x8A7CFF) // violet — AI coaching / secondary

    static let ok = Color(hex: 0x3DD68C) // aurora green
    static let warn = Color(hex: 0xF5B14C) // amber
    static let bad = Color(hex: 0xFF5C6C) // warm red
    static let info = Color(hex: 0x6AA8FF) // soft blue

    // mastery emission ramp (matches the desktop / pgre.py faces)
    private static let m0 = (r: 1.0, g: 0.298, b: 0.298) // #FF4C4C
    private static let m50 = (r: 0.961, g: 0.694, b: 0.298) // #F5B14C
    private static let m100 = (r: 0.239, g: 0.839, b: 0.549) // #3DD68C

    /// Mastery color for a fraction 0…1, interpolated red → amber → green.
    static func mastery(_ p: Double) -> Color {
        let t = min(max(p, 0), 1)
        let (a, b, local): ((r: Double, g: Double, b: Double), (r: Double, g: Double, b: Double), Double)
        if t < 0.5 {
            (a, b, local) = (m0, m50, t / 0.5)
        } else {
            (a, b, local) = (m50, m100, (t - 0.5) / 0.5)
        }
        return Color(
            .sRGB,
            red: a.r + (b.r - a.r) * local,
            green: a.g + (b.g - a.g) * local,
            blue: a.b + (b.b - a.b) * local)
    }
}

// MARK: - Typography

extension Font {
    static let pgDisplay = Font.system(.largeTitle, design: .rounded).weight(.bold)
    static let pgTitle = Font.system(.title2, design: .default).weight(.semibold)
    static let pgBody = Font.system(.body)
    static func pgMono(_ size: CGFloat, weight: Font.Weight = .medium) -> Font {
        .system(size: size, weight: weight, design: .monospaced)
    }
}

// MARK: - Cosmic background (procedural starfield)

struct ObservatoryBackground: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    /// Deterministic star field (seeded LCG so it never flickers between draws).
    private static let stars: [(x: Double, y: Double, r: Double, a: Double)] = {
        var seed: UInt64 = 0x9E37_79B9_7F4A_7C15
        func next() -> Double {
            seed = seed &* 6364136223846793005 &+ 1442695040888963407
            return Double(seed >> 11) / Double(1 << 53)
        }
        return (0..<150).map { _ in
            (x: next(), y: next(), r: 0.4 + next() * 1.3, a: 0.25 + next() * 0.55)
        }
    }()

    var body: some View {
        ZStack {
            // base glow: top-centre cool wash fading to deep space
            RadialGradient(
                colors: [Palette.space2, Palette.space],
                center: .init(x: 0.5, y: -0.1),
                startRadius: 0, endRadius: 620)
            // faint violet nebula in a corner
            RadialGradient(
                colors: [Palette.accent2.opacity(0.10), .clear],
                center: .init(x: 0.9, y: 0.08),
                startRadius: 0, endRadius: 360)
            Canvas { ctx, size in
                for s in Self.stars {
                    let rect = CGRect(
                        x: s.x * size.width, y: s.y * size.height,
                        width: s.r, height: s.r)
                    ctx.fill(Path(ellipseIn: rect), with: .color(Palette.text.opacity(s.a)))
                }
            }
            .allowsHitTesting(false)
        }
        .ignoresSafeArea()
        .background(Palette.space.ignoresSafeArea())
    }
}

// MARK: - Reusable components

/// Mono uppercase eyebrow (physics label / count).
struct Eyebrow: View {
    let text: String
    init(_ text: String) { self.text = text }
    var body: some View {
        Text(text.uppercased())
            .font(.pgMono(11))
            .tracking(1.6)
            .foregroundColor(Palette.textDim)
    }
}

/// Glass panel modifier — hairline border, subtle fill, rounded.
struct GlassCard: ViewModifier {
    var padding: CGFloat = 16
    var glow: Color? = nil
    func body(content: Content) -> some View {
        content
            .padding(padding)
            .background(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .fill(Palette.panel))
            .overlay(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .strokeBorder(glow ?? Palette.line, lineWidth: 1))
            .shadow(color: glow?.opacity(0.35) ?? .clear, radius: glow == nil ? 0 : 16)
    }
}

extension View {
    func glassCard(padding: CGFloat = 16, glow: Color? = nil) -> some View {
        modifier(GlassCard(padding: padding, glow: glow))
    }
}

/// A small monospaced count chip (deck rows). Kind sets the accent.
struct CountChip: View {
    enum Kind { case new, learn, review
        var color: Color {
            switch self {
            case .new: return Palette.info
            case .learn: return Palette.warn
            case .review: return Palette.ok
            }
        }
    }
    let count: Int
    let kind: Kind
    var body: some View {
        Text("\(count)")
            .font(.pgMono(13, weight: .semibold))
            .foregroundColor(count == 0 ? Palette.textFaint : kind.color)
            .frame(minWidth: 22)
    }
}

/// Small mastery ring for deck rows.
struct MasteryRing: View {
    var pct: Double // 0…1
    var size: CGFloat = 30
    var body: some View {
        ZStack {
            Circle().stroke(Palette.line, lineWidth: 3)
            Circle()
                .trim(from: 0, to: max(0.001, min(pct, 1)))
                .stroke(Palette.mastery(pct), style: .init(lineWidth: 3, lineCap: .round))
                .rotationEffect(.degrees(-90))
        }
        .frame(width: size, height: size)
    }
}

/// The score gauge: a value arc, an optional fainter Wilson band arc, a
/// confidence pip, and caller-supplied centre content. Abstain is drawn by the
/// caller as a dim node (see `.dimmed`).
struct GaugeRing<Center: View>: View {
    var fraction: Double // 0…1 main arc
    var band: ClosedRange<Double>? = nil // fainter uncertainty arc, 0…1
    var color: Color = Palette.accent
    var dimmed: Bool = false
    var lineWidth: CGFloat = 12
    var size: CGFloat = 132
    @ViewBuilder var center: () -> Center

    var body: some View {
        ZStack {
            Circle().stroke(Palette.line, lineWidth: lineWidth)
            if let band = band, !dimmed {
                Circle()
                    .trim(from: min(band.lowerBound, 1), to: min(band.upperBound, 1))
                    .stroke(color.opacity(0.28), style: .init(lineWidth: lineWidth + 6, lineCap: .round))
                    .rotationEffect(.degrees(-90))
            }
            Circle()
                .trim(from: 0, to: dimmed ? 0 : max(0.001, min(fraction, 1)))
                .stroke(
                    dimmed ? Palette.line : color,
                    style: .init(lineWidth: lineWidth, lineCap: .round))
                .rotationEffect(.degrees(-90))
                .shadow(color: dimmed ? .clear : color.opacity(0.5), radius: 8)
            center()
        }
        .frame(width: size, height: size)
    }
}

/// Shared empty / error / loading states (one component instead of repeated glyphs).
struct StatusState: View {
    enum Kind { case loading(String), empty(String, String), error(String) }
    let kind: Kind
    var body: some View {
        VStack(spacing: 12) {
            switch kind {
            case let .loading(msg):
                ProgressView().tint(Palette.accent)
                Text(msg).font(.pgMono(12)).foregroundColor(Palette.textDim)
            case let .empty(glyph, msg):
                Text(glyph).font(.system(size: 34)).foregroundColor(Palette.textFaint)
                Text(msg).font(.pgBody).foregroundColor(Palette.textDim)
                    .multilineTextAlignment(.center)
            case let .error(msg):
                Image(systemName: "exclamationmark.triangle").foregroundColor(Palette.warn)
                Text(msg).font(.pgBody).foregroundColor(Palette.textDim)
                    .multilineTextAlignment(.center)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding(24)
    }
}
